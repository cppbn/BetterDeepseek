<template>
  <div class="relative">
    <button
      @click.stop="toggleDropdown"
      class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm hover:bg-gray-100 transition-colors"
    >
      <CpuChipIcon class="w-4 h-4 text-gray-500" />
      <span class="max-w-[150px] truncate">{{ currentModelName }}</span>
      <ChevronDownIcon class="w-4 h-4 text-gray-400" />
    </button>

    <Transition name="fade">
      <div
        v-if="isOpen"
        v-click-outside="closeDropdown"
        class="absolute top-full left-0 mt-1 w-72 bg-white rounded-lg shadow-lg border border-gray-200 z-50 max-h-96 overflow-y-auto"
      >
        <div class="p-2">
          <div class="text-xs font-medium text-gray-500 mb-2 px-2">选择模型</div>
          <div
            v-for="(info, key) in models"
            :key="key"
            @click="selectModel(key)"
            class="flex items-center justify-between p-2 rounded-md cursor-pointer hover:bg-gray-50 transition-colors"
            :class="{ 'bg-blue-50': selectedModel === key }"
          >
            <div class="flex-1">
              <div class="font-medium text-sm">{{ formatModelName(key) }}</div>
              <div class="text-xs text-gray-500 flex items-center gap-2 mt-0.5">
                <span>{{ info.provider }}</span>
                <span v-if="info.accept_image" class="flex items-center gap-0.5">
                  <PhotoIcon class="w-3 h-3" />
                </span>
                <span v-if="info.accept_audio" class="flex items-center gap-0.5">
                  <SpeakerWaveIcon class="w-3 h-3" />
                </span>
              </div>
            </div>
            <CheckIcon v-if="selectedModel === key" class="w-4 h-4 text-blue-600" />
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import {
  CpuChipIcon,
  ChevronDownIcon,
  CheckIcon,
  PhotoIcon,
  SpeakerWaveIcon,
} from '@heroicons/vue/24/outline';
import type { ModelsResponse } from '@/types';

const props = defineProps<{
  models: ModelsResponse;
  modelValue: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const isOpen = ref(false);

const selectedModel = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
});

const currentModelName = computed(() => {
  return formatModelName(selectedModel.value);
});

function formatModelName(key: string): string {
  // 将 key 转换为更友好的显示名称
  const nameMap: Record<string, string> = {
    'default': 'DeepSeek (默认)',
    'deepseek-v4-flash-thinking': 'DeepSeek V4 Flash',
    'deepseek-v4-pro-thinking': 'DeepSeek V4 Pro',
    'qwen3.6-plus-thinking': 'Qwen 3.6 Plus',
    'qwen3.5-flash-thinking': 'Qwen 3.5 Flash',
    'kimi-k2.6-thinking': 'Kimi K2.6',
    'glm-5.1-thinking': 'GLM 5.1',
    'mino-v2.5': 'MiMo V2.5',
  };
  return nameMap[key] || key;
}

function selectModel(key: string) {
  selectedModel.value = key;
  isOpen.value = false;
}

function closeDropdown() {
  isOpen.value = false;
}

function toggleDropdown() {
  isOpen.value = !isOpen.value;
}

// 全局点击监听，关闭下拉
function handleGlobalClick(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest('.relative')) {
    isOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleGlobalClick);
});

onUnmounted(() => {
  document.removeEventListener('click', handleGlobalClick);
});

</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>