<template>
  <div ref="containerRef" class="flex-1 overflow-y-auto p-2 md:p-4 space-y-3 md:space-y-4 bg-white">
    <div v-if="isLoading" class="flex justify-center py-8">
      <LoadingSpinner class="w-8 h-8 text-blue-600" />
    </div>
    <template v-else>
      <div class="max-w-3xl mx-auto space-y-4">
        <div v-for="message in messages" :key="message.id">
          <MessageItem
            :message="message"
            @edit="(m) => $emit('edit', m)"
            @delete="(m) => $emit('delete', m)"
            @regenerate="(m) => $emit('regenerate', m)"
          />
        </div>
        <div v-if="messages.length === 0" class="text-center text-gray-400 py-8">
          开始新对话吧
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import MessageItem from './MessageItem.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';
import type { Message } from '@/types';

const props = defineProps<{
  messages: Message[];
  isLoading?: boolean;
}>();

defineEmits<{
  (e: 'edit', message: Message): void;
  (e: 'delete', message: Message): void;
  (e: 'regenerate', message: Message): void;
}>();

const containerRef = ref<HTMLElement | null>(null);

watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      if (containerRef.value) {
        containerRef.value.scrollTop = containerRef.value.scrollHeight;
      }
    });
  }
);
</script>

<style scoped>
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>