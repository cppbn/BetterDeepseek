<template>
  <div
    class="flex group"
    :class="[message.role === 'user' ? 'justify-end' : 'justify-start']"
    @mouseenter="showActions = true"
    @mouseleave="showActions = false"
    @click="togglePinActions"
  >
    <div
      v-if="message.role === 'user' && message.type === 'message' && !message.isStreaming && (showActions || pinnedActions)"
      class="flex items-center gap-0.5 mr-1 self-end mb-1"
    >
      <button
        @click="copyContent"
        class="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        :title="copied ? '已复制' : '复制'"
      >
        <CheckIcon v-if="copied" class="w-4 h-4 text-green-500" />
        <ClipboardIcon v-else class="w-4 h-4" />
      </button>
      <button
        @click="$emit('edit', message)"
        class="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        title="编辑"
      >
        <PencilIcon class="w-4 h-4" />
      </button>
      <button
        @click="confirmDelete"
        class="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
        title="删除"
      >
        <TrashIcon class="w-4 h-4" />
      </button>
    </div>

    <div
      class="max-w-[85%] rounded-2xl px-5 py-3 shadow-sm"
      :class="{
        'bg-blue-600 text-white': message.role === 'user',
        'bg-white text-gray-800 border border-gray-100': message.role !== 'user' && message.type !== 'reasoning',
        'bg-gray-50 border border-gray-100': message.type === 'reasoning',
      }"
    >
      <template v-if="message.type === 'reasoning'">
        <div
          class="flex items-center gap-2 cursor-pointer select-none"
          :class="{ 'py-1.5 px-3 -mx-5 -my-3': false }"
          @click="toggleCollapse"
        >
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-3.5 h-3.5 text-gray-400" />
          <LightBulbIcon class="w-3.5 h-3.5 text-gray-400" />
          <span class="text-xs font-medium text-gray-500">推理过程</span>
          <span v-if="collapsed && stepSummary" class="text-xs text-gray-400 ml-1">{{ stepSummary }}</span>
        </div>
        <div v-if="!collapsed" class="mt-3 space-y-2">
          <template v-if="message.reasoningSteps?.length">
            <div
              v-for="(step, i) in message.reasoningSteps"
              :key="i"
              class="text-xs text-gray-500 leading-relaxed"
              :class="step.type === 'thinking' ? 'whitespace-pre-wrap break-words' : ''"
            >
              <template v-if="step.type === 'thinking'">
                {{ step.content }}
              </template>
              <template v-else-if="step.type === 'tool_call'">
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div
                    class="flex items-center gap-1.5 cursor-pointer select-none px-2.5 py-2"
                    @click="toggleToolCall(i)"
                  >
                    <WrenchScrewdriverIcon class="w-3 h-3 text-yellow-600 flex-shrink-0" />
                    <span class="font-medium text-xs text-yellow-700 truncate">{{ step.toolName }}</span>
                    <span
                      v-if="!expandedToolCalls.has(i) && getToolSummary(step)"
                      class="text-xs text-yellow-500/70 ml-1 truncate hidden sm:inline"
                    >{{ getToolSummary(step) }}</span>
                    <component
                      :is="expandedToolCalls.has(i) ? ChevronDownIcon : ChevronRightIcon"
                      class="w-3 h-3 text-yellow-400 ml-auto flex-shrink-0"
                    />
                  </div>
                  <div v-if="expandedToolCalls.has(i)" class="px-2.5 pb-2 space-y-1.5">
                    <template v-if="step.toolArgs && Object.keys(step.toolArgs).length">
                      <template v-if="isCodeTool(step.toolName || '') && step.toolArgs.code">
                        <pre
                          class="text-xs bg-gray-900 text-gray-100 rounded p-2 overflow-auto max-h-40 font-mono leading-relaxed"
                          v-html="highlightCode(String(step.toolArgs.code), codeHighlightLang(step.toolName || ''))"
                        ></pre>
                        <div
                          v-if="otherCodeArgs(step.toolArgs).length"
                          class="text-xs text-yellow-700 bg-yellow-100/60 rounded p-1.5 font-mono whitespace-pre-wrap leading-relaxed"
                        >{{ otherCodeArgs(step.toolArgs) }}</div>
                      </template>
                      <div
                        v-else
                        class="text-xs text-yellow-700 bg-yellow-100/60 rounded p-1.5 font-mono whitespace-pre-wrap leading-relaxed"
                      >{{ formatToolArgs(step.toolArgs) }}</div>
                    </template>
                    <template v-if="step.toolResult">
                      <template v-if="isSearchTool(step.toolName || '') && parsedSearchResults[i]">
                        <div v-if="parsedSearchResults[i].answer"
                             class="text-xs text-blue-700 bg-blue-50 rounded p-1.5 border border-blue-100">
                          <span class="font-medium">AI 摘要：</span>{{ parsedSearchResults[i].answer }}
                        </div>
                        <div
                          v-for="sr in parsedSearchResults[i].results"
                          :key="sr.index"
                          class="text-xs bg-white rounded border border-gray-100 p-1.5 space-y-0.5"
                        >
                          <a
                            :href="sr.url"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="font-medium text-blue-600 hover:underline line-clamp-1 block"
                          >{{ sr.title }}</a>
                          <p class="text-gray-500 line-clamp-3">{{ sr.snippet }}</p>
                        </div>
                      </template>
                      <template v-else-if="isCodeTool(step.toolName || '')">
                        <div
                          class="text-xs text-gray-600 bg-gray-100 rounded p-1.5 max-h-32 overflow-y-auto font-mono whitespace-pre-wrap leading-relaxed"
                        >{{ step.toolResult }}</div>
                      </template>
                      <div
                        v-else
                        class="text-xs text-green-700 bg-green-50 rounded p-1.5 border border-green-100 whitespace-pre-wrap break-words max-h-32 overflow-y-auto"
                      >{{ step.toolResult }}</div>
                    </template>
                    <div
                      v-else-if="step.toolResultLoading"
                      class="flex items-center gap-1.5 text-xs text-gray-400 py-1"
                    >
                      <span class="inline-block w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span>
                      执行中...
                    </div>
                    <div v-else class="text-xs text-gray-400 py-1">无输出</div>
                  </div>
                </div>
              </template>
            </div>
          </template>
          <div
            v-else-if="message.content"
            class="whitespace-pre-wrap break-words text-xs text-gray-500 leading-relaxed"
          >
            {{ message.content }}
          </div>
        </div>
      </template>

      <template v-else-if="message.type === 'tool_call'">
        <div class="flex items-center gap-2 cursor-pointer select-none" @click="toggleCollapse">
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-3.5 h-3.5" />
          <WrenchScrewdriverIcon class="w-3.5 h-3.5" />
          <span class="text-xs font-medium">调用工具: {{ message.toolCallData?.name || JSON.parse(message.content).name }}</span>
        </div>
        <div v-if="!collapsed" class="mt-2">
          <pre class="text-xs overflow-auto">{{
            JSON.stringify(message.toolCallData?.args || JSON.parse(message.content).args, null, 2)
          }}</pre>
        </div>
      </template>

      <template v-else-if="message.type === 'tool_result'">
        <div class="flex items-center gap-2 cursor-pointer select-none" @click="toggleCollapse">
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-3.5 h-3.5" />
          <CheckCircleIcon class="w-3.5 h-3.5 text-green-600" />
          <span class="text-xs font-medium">工具结果</span>
        </div>
        <div v-if="!collapsed" class="mt-2 text-xs whitespace-pre-wrap break-words">
          {{ parseToolResult(message.content) }}
        </div>
      </template>

      <template v-else>
        <div v-if="message.role === 'assistant' && message.type === 'message'" class="break-words">
          <MarkdownRenderer :content="message.content"></MarkdownRenderer>
        </div>
        <div v-else class="whitespace-pre-wrap break-words">
          {{ message.content }}
        </div>
      </template>
      <div
        v-if="(message.attachments_file_id?.length || message.attachments?.length)"
        class="mt-3 pt-2 border-t border-gray-200"
      >
        <div class="text-xs font-medium text-gray-600 mb-1">附件</div>
        <div v-for="fileId in message.attachments_file_id" :key="fileId" class="flex items-center gap-2 text-sm">
          
          <FileIcon class="w-4 h-4 text-gray-500" />
          <span class="flex-1 truncate text-gray-700">
            {{ fileInfoMap[fileId]?.original_filename || fileId }}
          </span>
          <button
            @click="previewFile(fileId)"
            class="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100"
            :disabled="loadingMap[fileId]"
          >
            预览
          </button>
          <button
            @click="downloadFile(fileId)"
            class="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            :disabled="loadingMap[fileId]"
          >
            下载
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="message.role === 'assistant' && message.type === 'message' && !message.isStreaming && (showActions || pinnedActions)"
      class="flex items-center gap-0.5 ml-1 self-end mb-1"
    >
      <button
        @click="copyContent"
        class="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        :title="copied ? '已复制' : '复制'"
      >
        <CheckIcon v-if="copied" class="w-4 h-4 text-green-500" />
        <ClipboardIcon v-else class="w-4 h-4" />
      </button>
      <button
        v-if="isLastAssistantMessage"
        @click="$emit('regenerate', message)"
        class="p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
        title="重新生成"
      >
        <ArrowPathIcon class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import {
  WrenchScrewdriverIcon,
  CheckCircleIcon,
  LightBulbIcon,
  DocumentIcon as FileIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ClipboardIcon,
  CheckIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline';
import type { Message, FileInfo, ReasoningStep } from '@/types';
import MarkdownRenderer from './MarkdownRenderer.vue';
import { filesApi } from '@/api/files';
import { useSessionStore } from '@/stores/session';
import hljs from 'highlight.js';

const props = defineProps<{
  message: Message;
}>();

const emit = defineEmits<{
  (e: 'edit', message: Message): void;
  (e: 'delete', message: Message): void;
  (e: 'regenerate', message: Message): void;
}>();

const sessionStore = useSessionStore();

const showActions = ref(false);
const pinnedActions = ref(false);
const copied = ref(false);

function togglePinActions() {
  pinnedActions.value = !pinnedActions.value;
}

const isLastAssistantMessage = computed(() => {
  const msgs = sessionStore.currentMessages;
  if (!msgs.length) return false;
  const lastMsg = msgs[msgs.length - 1];
  if (!lastMsg) return false;
  return (
    lastMsg.id === props.message.id &&
    lastMsg.role === 'assistant' &&
    lastMsg.type === 'message' &&
    !lastMsg.isStreaming
  );
});

const collapsed = ref(true);

function initCollapsed() {
  if (props.message.type === 'reasoning') {
    return false;
  }
  if (props.message.type === 'tool_call' || props.message.type === 'tool_result') {
    return true;
  }
  return false;
}

collapsed.value = initCollapsed();

function toggleCollapse() {
  if (['reasoning', 'tool_call', 'tool_result'].includes(props.message.type)) {
    collapsed.value = !collapsed.value;
  }
}

const stepSummary = computed(() => {
  if (!props.message.reasoningSteps?.length) return '';
  const thinkingCount = props.message.reasoningSteps.filter(s => s.type === 'thinking').length;
  const toolCount = props.message.reasoningSteps.filter(s => s.type === 'tool_call').length;
  const parts: string[] = [];
  if (thinkingCount) parts.push(`${thinkingCount} 步思考`);
  if (toolCount) parts.push(`${toolCount} 次工具调用`);
  return `(${parts.join('，')})`;
});

const expandedToolCalls = reactive(new Set<number>());

function toggleToolCall(index: number) {
  if (expandedToolCalls.has(index)) {
    expandedToolCalls.delete(index);
  } else {
    expandedToolCalls.add(index);
  }
}

function parseToolResult(raw: string): string {
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object' && typeof parsed.content === 'string') {
      return parsed.content;
    }
  } catch { /* not JSON */ }
  return raw;
}

const SEARCH_TOOLS = new Set(['web_search', 'tavily_search', 'tavily_extract', 'tavily_crawl', 'tavily_map']);
const CODE_TOOLS = new Set(['exec_python', 'exec_shell']);
const FILE_TOOLS = new Set(['read_txt', 'read_image', 'read_audio', 'describe_image', 'describe_audio', 'export_file', 'list_files']);

function isSearchTool(name: string): boolean {
  return SEARCH_TOOLS.has(name);
}

function isCodeTool(name: string): boolean {
  return CODE_TOOLS.has(name);
}

function formatToolArgs(args: Record<string, unknown>): string {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(args)) {
    if (value === undefined || value === null || value === '') continue;
    if (typeof value === 'string') {
      lines.push(`${key} = ${value}`);
    } else {
      lines.push(`${key} = ${JSON.stringify(value)}`);
    }
  }
  return lines.join('\n');
}

interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  index?: string;
}

interface SearchResultData {
  results: SearchResultItem[];
  answer?: string;
}

function parseSearchResult(raw: string): SearchResultData | null {
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.results && Array.isArray(parsed.results)) {
      return {
        results: parsed.results.map((r: any) => ({
          title: r.title || '',
          url: r.url || '',
          snippet: r.snippet || '',
          index: r.index || '',
        })),
        answer: parsed.answer || undefined,
      };
    }
  } catch { /* not JSON */ }
  return null;
}

const parsedSearchResults = computed(() => {
  const map: Record<number, SearchResultData> = {};
  props.message.reasoningSteps?.forEach((step, i) => {
    if (isSearchTool(step.toolName || '') && step.toolResult) {
      const parsed = parseSearchResult(step.toolResult);
      if (parsed) map[i] = parsed;
    }
  });
  return map;
});

function highlightCode(code: string, lang?: string): string {
  try {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  } catch {
    return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

function codeHighlightLang(toolName: string): string {
  if (toolName === 'exec_python') return 'python';
  if (toolName === 'exec_shell') return 'bash';
  return 'plaintext';
}

function otherCodeArgs(args: Record<string, unknown>): string {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(args)) {
    if (key === 'code' || value === undefined || value === null || value === '') continue;
    lines.push(`${key} = ${typeof value === 'string' ? value : JSON.stringify(value)}`);
  }
  return lines.join('\n');
}

function getToolSummary(step: ReasoningStep): string {
  if (step.toolResultLoading) return '执行中...';
  if (!step.toolResult) return '';

  if (FILE_TOOLS.has(step.toolName || '')) {
    if (step.toolName === 'list_files' && step.toolResult) {
      const lines = step.toolResult.split('\n').filter(l => l.trim());
      if (lines.length) return `${lines.length} 个文件`;
      return '';
    }
    const args = step.toolArgs as Record<string, unknown> | undefined;
    if (args?.file_path) return String(args.file_path);
    if (args?.path) return String(args.path);
    return '';
  }

  if (isCodeTool(step.toolName || '')) return '';

  if (isSearchTool(step.toolName || '')) {
    const parsed = parseSearchResult(step.toolResult);
    if (parsed?.results?.length) {
      const parts = [`${parsed.results.length} 条结果`];
      if (parsed.answer) parts.push('含 AI 摘要');
      return parts.join('，');
    }
  }

  const preview = step.toolResult.slice(0, 40);
  return preview.length < step.toolResult.length ? `${preview}...` : preview;
}

async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content);
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = props.message.content;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 2000);
}

function confirmDelete() {
  const confirmed = window.confirm('确定要删除这条消息吗？后续消息也会被删除。');
  if (confirmed) {
    emit('delete', props.message);
  }
}

const fileInfoMap = reactive<Record<string, FileInfo>>({});
const loadingMap = reactive<Record<string, boolean>>({});

// 预览文件：在新标签页中打开 blob URL（移动端 iframe 不支持 blob URL）
async function previewFile(fileId: string) {
  if (!sessionStore.currentSessionId) return;
  // 同步打开空白窗口，避免异步请求后被浏览器拦截弹出窗口
  const previewWindow = window.open('', '_blank');
  if (!previewWindow) {
    alert('请允许弹出窗口以预览文件');
    return;
  }
  try {
    const response = await filesApi.getFileBlob(sessionStore.currentSessionId, fileId);
    const url = URL.createObjectURL(response.data);
    previewWindow.location.href = url;
  } catch (error) {
    console.error('预览失败:', error);
    previewWindow.close();
    alert('预览失败，请稍后重试');
  }
}

// 下载函数保持不变（但使用原始 blob）
async function downloadFile(fileId: string) {
  if (!sessionStore.currentSessionId) return;
  const fileName = fileInfoMap[fileId]?.original_filename;
  try {
    await filesApi.download(sessionStore.currentSessionId, fileId, fileName);
  } catch (error) {
    console.error('下载失败:', error);
    alert('下载失败');
  }
}

// 获取文件信息（原有逻辑）
async function fetchFileInfo(fileId: string) {
  if (fileInfoMap[fileId] || loadingMap[fileId]) return;
  if (!sessionStore.currentSessionId) return;
  loadingMap[fileId] = true;
  try {
    const { data } = await filesApi.getFileInfo(sessionStore.currentSessionId, fileId);
    fileInfoMap[fileId] = data;
  } catch (error) {
    console.error('获取文件信息失败:', error);
  } finally {
    loadingMap[fileId] = false;
  }
}

onMounted(() => {
  if (props.message.attachments_file_id) {
    props.message.attachments_file_id.forEach(fetchFileInfo);
  }
});
</script>