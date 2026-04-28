<template>
  <div
    class="flex group"
    :class="[message.role === 'user' ? 'justify-end' : 'justify-start']"
    @mouseenter="showActions = true"
    @mouseleave="showActions = false"
    @click="togglePinActions"
  >
    <!-- Action buttons for user messages (left side of bubble) -->
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
        'bg-white text-gray-800 border border-gray-100': message.role !== 'user',
        'italic text-gray-500 text-sm bg-gray-50': message.type === 'reasoning',
        'bg-yellow-50 border border-yellow-200 text-yellow-800': message.type === 'tool_call',
        'bg-purple-50 border border-purple-200 text-purple-800': message.type === 'tool_result',
      }"
    >
      <!-- 推理消息 -->
      <template v-if="message.type === 'reasoning'">
        <div class="flex items-center gap-2 cursor-pointer select-none" @click="toggleCollapse">
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-4 h-4 text-gray-500" />
          <LightBulbIcon class="w-4 h-4 text-gray-500" />
          <span class="text-sm font-medium text-gray-600">推理过程</span>
          <!-- <span v-if="message.isStreaming" class="text-xs text-gray-400 ml-2 animate-pulse">生成中...</span> -->
        </div>
        <div v-if="!collapsed" class="mt-2 whitespace-pre-wrap break-words text-xs text-gray-500 leading-relaxed">
          {{ message.content }}
          <!-- <span v-if="message.isStreaming" class="inline-block w-2 h-3 ml-1 bg-gray-400 animate-pulse"></span> -->
        </div>
      </template>

      <!-- 工具调用消息 -->
      <template v-else-if="message.type === 'tool_call'">
        <div class="flex items-center gap-2 cursor-pointer select-none" @click="toggleCollapse">
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-4 h-4" />
          <WrenchScrewdriverIcon class="w-4 h-4" />
          <span class="text-sm font-medium">调用工具: {{ message.toolCallData?.name || JSON.parse(message.content).name }}</span>
        </div>
        <div v-if="!collapsed" class="mt-2">
          <pre class="text-xs overflow-auto">{{
            JSON.stringify(message.toolCallData?.args || JSON.parse(message.content).args, null, 2)
          }}</pre>
        </div>
      </template>

      <!-- 工具结果消息 -->
      <template v-else-if="message.type === 'tool_result'">
        <div class="flex items-center gap-2 cursor-pointer select-none" @click="toggleCollapse">
          <component :is="collapsed ? ChevronRightIcon : ChevronDownIcon" class="w-4 h-4" />
          <CheckCircleIcon class="w-4 h-4 text-green-600" />
          <span class="text-sm font-medium">工具结果</span>
        </div>
        <div v-if="!collapsed" class="mt-2 text-sm whitespace-pre-wrap break-words">
          {{ message.content }}
        </div>
      </template>

      <template v-else>
        <div v-if="message.role === 'assistant' && message.type === 'message'" class="break-words">
          <MarkdownRenderer :content="message.content"></MarkdownRenderer>
          <span v-if="message.isStreaming" class="inline-block w-2 h-4 ml-1 bg-current animate-pulse align-middle"></span>
        </div>
        <div v-else class="whitespace-pre-wrap break-words">
          {{ message.content }}
          <span v-if="message.isStreaming" class="inline-block w-2 h-4 ml-1 bg-current animate-pulse"></span>
        </div>
      </template>
      <!-- 附件列表（助手消息且存在附件 ID） -->
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

    <!-- Action buttons for assistant messages (right side of bubble) -->
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
import type { Message, FileInfo } from '@/types';
import MarkdownRenderer from './MarkdownRenderer.vue';
import { filesApi } from '@/api/files';
import { useSessionStore } from '@/stores/session';

const props = defineProps<{ message: Message }>();

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

// 折叠状态（独立于消息对象）
const collapsed = ref(true);

// 根据消息类型和流式状态决定初始折叠
function initCollapsed() {
  // 推理消息：默认展开
  if (props.message.type === 'reasoning') {
    return false;
  }
  // 工具调用和工具结果：默认折叠
  if (props.message.type === 'tool_call' || props.message.type === 'tool_result') {
    return true;
  }
  // 其他类型无折叠功能
  return false;
}

// 初始化折叠状态
collapsed.value = initCollapsed();

function toggleCollapse() {
  // 仅对可折叠类型生效
  if (['reasoning', 'tool_call', 'tool_result'].includes(props.message.type)) {
    collapsed.value = !collapsed.value;
  }
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