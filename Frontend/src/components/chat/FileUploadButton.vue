<template>
  <div>
    <input
      ref="fileInputRef"
      type="file"
      multiple
      class="hidden"
      @change="handleFileChange"
      :disabled="disabled"
    />
    <button
      @click="fileInputRef?.click()"
      :disabled="disabled"
      class="p-2 rounded-full hover:bg-gray-100 transition-colors disabled:opacity-50"
      title="上传文件"
    >
      <PaperClipIcon class="w-5 h-5 text-gray-500" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { PaperClipIcon } from '@heroicons/vue/24/outline';

const props = defineProps<{
  sessionId: string | null;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'files-selected', files: File[]): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  if (!files || files.length === 0 || !props.sessionId) return;

  emit('files-selected', Array.from(files));
  
  // 清空 input 值，以便再次选择相同文件时仍能触发
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
}
</script>