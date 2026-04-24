<template>
  <div class="border-t border-gray-200 bg-white p-4">
    <div class="max-w-3xl mx-auto">
      <!-- 工具条 -->
      <div class="flex items-center gap-3 mb-2">
        <button
          @click="toggleSearch"
          :class="[
            'flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors',
            enableSearch
              ? 'bg-blue-50 text-blue-600 border border-blue-200'
              : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
          ]"
        >
          <GlobeAltIcon class="w-4 h-4" />
          <span>联网搜索</span>
        </button>
        <button
          @click="toggleCodeExec"
          :class="[
            'flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors',
            enableCodeExec
              ? 'bg-blue-50 text-blue-600 border border-blue-200'
              : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
          ]"
        >
          <CodeBracketIcon class="w-4 h-4" />
          <span>代码执行</span>
        </button>
      </div>

      <!-- 拖拽上传区域 -->
      <div
        ref="dropZoneRef"
        class="relative"
        @dragenter="handleDragEnter"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
      >
        <!-- 拖拽遮罩 -->
        <div
          v-if="isDragging"
          class="absolute inset-0 bg-blue-50/80 backdrop-blur-sm rounded-xl border-2 border-blue-400 border-dashed z-10 flex items-center justify-center pointer-events-none"
        >
          <div class="text-blue-600 font-medium flex items-center gap-2">
            <DocumentArrowUpIcon class="w-6 h-6" />
            <span>释放文件以上传</span>
          </div>
        </div>

        <!-- 已选文件预览区（图片缩略图） -->
        <div v-if="selectedFiles.length > 0" class="mb-2 flex flex-wrap gap-2">
          <div
            v-for="file in selectedFiles"
            :key="file.tempId"
            class="flex items-center gap-2 bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm shadow-sm"
          >
            <div class="flex-shrink-0 w-6 h-6 flex items-center justify-center">
              <img
                v-if="file.previewUrl"
                :src="file.previewUrl"
                class="w-6 h-6 object-cover rounded"
                alt="preview"
              />
              <DocumentIcon v-else class="w-4 h-4 text-gray-500" />
            </div>
            <span class="truncate max-w-[150px]">{{ file.original_filename }}</span>
            <button @click="removeFile(file.tempId)" class="hover:text-red-500">
              <XMarkIcon class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="flex items-end gap-2">
          <div class="flex-1 relative">
            <textarea
              ref="textareaRef"
              v-model="inputText"
              :disabled="disabled"
              @keydown="handleKeydown"
              placeholder="输入消息... (Enter 换行，Ctrl+Enter 发送)"
              rows="3"
              class="w-full resize-y rounded-xl border border-gray-200 bg-white text-gray-900 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-shadow"
              :style="{ minHeight: '80px', maxHeight: '200px' }"
            ></textarea>
            <div class="absolute right-3 bottom-3 flex gap-1">
              <FileUploadButton
                :session-id="sessionId"
                :disabled="disabled"
                @files-selected="handleFilesSelected"
              />
            </div>
          </div>

          <button
            v-if="isStreaming"
            @click="$emit('stop')"
            class="p-3 rounded-xl bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors shadow-sm"
            title="停止生成"
          >
            <StopIcon class="w-5 h-5" />
          </button>

          <button
            v-else
            @click="sendMessage"
            :disabled="!canSend || disabled"
            class="p-3 rounded-xl bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 transition-colors shadow-sm"
          >
            <PaperAirplaneIcon class="w-5 h-5" />
          </button>
        </div>
      </div>

      <div class="mt-2 text-xs text-gray-400 flex justify-between">
        <span>支持拖拽或点击上传文件</span>
        <span>Enter 换行，Ctrl+Enter 发送</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import {
  PaperAirplaneIcon,
  DocumentIcon,
  XMarkIcon,
  GlobeAltIcon,
  CodeBracketIcon,
  DocumentArrowUpIcon,
  StopIcon,
} from '@heroicons/vue/24/outline';
import FileUploadButton from './FileUploadButton.vue';
import { filesApi } from '@/api/files';

// 本地文件记录（包含预览URL和上传后的file_id）
interface SelectedFile {
  tempId: string;              // 临时唯一标识
  file_id?: string;            // 后端返回的文件ID
  original_filename: string;
  previewUrl?: string;         // 图片预览的 blob URL
  file_size?: number;
}

const props = defineProps<{
  sessionId: string | null;
  disabled?: boolean;
  isStreaming?: boolean;
}>();

const emit = defineEmits<{
  (e: 'send', message: string, attachments?: string[], enableSearch?: boolean, enableCodeExec?: boolean): void;
  (e: 'stop'): void; 
}>();

const inputText = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const selectedFiles = ref<SelectedFile[]>([]);
const enableSearch = ref(true);
const enableCodeExec = ref(true);
const isDragging = ref(false);
const dropZoneRef = ref<HTMLElement | null>(null);

const canSend = computed(() => inputText.value.trim().length > 0 || selectedFiles.value.length > 0);

// 生成图片预览URL（仅图片类型）
function createPreviewUrl(file: File): string | undefined {
  if (file.type.startsWith('image/')) {
    return URL.createObjectURL(file);
  }
  return undefined;
}

// 核心上传函数：先显示预览，再异步上传获取file_id
async function uploadFiles(files: File[]) {
  if (!props.sessionId) return;

  // 1. 为每个文件创建临时记录（立即显示预览）
  const tempFiles: SelectedFile[] = files.map(file => ({
    tempId: `temp-${Date.now()}-${Math.random()}`,
    original_filename: file.name,
    previewUrl: createPreviewUrl(file),
    file_size: file.size,
  }));
  selectedFiles.value.push(...tempFiles);

  // 2. 逐个上传，更新file_id
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const tempFile = tempFiles[i];
    try {
      const { data } = await filesApi.upload(props.sessionId, file);
      const idx = selectedFiles.value.findIndex(f => f.tempId === tempFile.tempId);
      if (idx !== -1) {
        selectedFiles.value[idx].file_id = data.file_id;
        selectedFiles.value[idx].file_size = data.file_size;
      }
    } catch (error) {
      console.error('Upload failed:', file.name, error);
      // 上传失败则移除该项并释放预览URL
      const idx = selectedFiles.value.findIndex(f => f.tempId === tempFile.tempId);
      if (idx !== -1) {
        if (selectedFiles.value[idx].previewUrl) {
          URL.revokeObjectURL(selectedFiles.value[idx].previewUrl!);
        }
        selectedFiles.value.splice(idx, 1);
      }
    }
  }
}

// 处理按钮选择的文件
function handleFilesSelected(files: File[]) {
  uploadFiles(files);
}

// 移除文件并释放预览URL
function removeFile(tempId: string) {
  const file = selectedFiles.value.find(f => f.tempId === tempId);
  if (file?.previewUrl) {
    URL.revokeObjectURL(file.previewUrl);
  }
  selectedFiles.value = selectedFiles.value.filter(f => f.tempId !== tempId);
}

// 发送消息
function sendMessage() {
  if (!canSend.value) return;
  const message = inputText.value.trim();
  const fileIds = selectedFiles.value
    .filter(f => f.file_id)   // 只包含已成功上传的
    .map(f => f.file_id!);
  emit('send', message, fileIds.length > 0 ? fileIds : undefined, enableSearch.value, enableCodeExec.value);
  
  // 清理
  selectedFiles.value.forEach(f => {
    if (f.previewUrl) URL.revokeObjectURL(f.previewUrl);
  });
  inputText.value = '';
  selectedFiles.value = [];
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto';
    }
  });
}

function toggleSearch() { enableSearch.value = !enableSearch.value; }
function toggleCodeExec() { enableCodeExec.value = !enableCodeExec.value; }

function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    sendMessage();
  }
}

// 拖拽事件
function handleDragEnter(e: DragEvent) {
  e.preventDefault();
  if (props.disabled) return;
  isDragging.value = true;
}
function handleDragOver(e: DragEvent) {
  e.preventDefault();
  if (props.disabled) return;
  e.dataTransfer!.dropEffect = 'copy';
}
function handleDragLeave(e: DragEvent) {
  e.preventDefault();
  isDragging.value = false;
}
async function handleDrop(e: DragEvent) {
  e.preventDefault();
  isDragging.value = false;
  if (props.disabled || !props.sessionId) return;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    await uploadFiles(Array.from(files));
  }
}
</script>