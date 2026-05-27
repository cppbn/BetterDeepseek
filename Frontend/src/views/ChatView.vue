<template>
  <AppLayout>
    <template #toolbar-left>
      <ModelSelector
        v-if="models"
        v-model="currentModel"
        :models="models"
      />
    </template>
    <template #toolbar-right>
      <button
        @click="handleNewSession"
        class="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
      >
        <PlusIcon class="w-4 h-4" />
        <span class="hidden sm:inline">新对话</span>
      </button>
    </template>
    <div class="flex-1 flex flex-col h-full">
      <MessageList
        :messages="sessionStore.currentMessages"
        :is-loading="sessionStore.isLoadingMessages"
        class="flex-1"
        @edit="handleEdit"
        @delete="handleDelete"
        @regenerate="handleRegenerate"
      />
      <ChatInput
        ref="chatInputRef"
        :session-id="sessionStore.currentSessionId"
        :is-streaming="isStreaming"
        :is-editing="editingMessageId != null"
        :disabled="!sessionStore.currentSessionId"
        @send="handleSendMessage"
        @stop="stop"
        @cancel-edit="handleCancelEdit"
      />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { watch, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { PlusIcon } from '@heroicons/vue/24/outline';
import AppLayout from '@/components/layout/AppLayout.vue';
import MessageList from '@/components/chat/MessageList.vue';
import ChatInput from '@/components/chat/ChatInput.vue';
import ModelSelector from '@/components/chat/ModelSelector.vue';
import { useSessionStore } from '@/stores/session';
import { useChatStream } from '@/composables/useChatStream';
import { modelsApi } from '@/api/models';
import type { ModelsResponse, Message } from '@/types';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const { sendMessage, isStreaming, stop, regenerate } = useChatStream();

const chatInputRef = ref<InstanceType<typeof ChatInput> | null>(null);
const editingMessageId = ref<number | null>(null);

const models = ref<ModelsResponse | null>(null);
const currentModel = ref<string>('default');

// 从 localStorage 加载上次选择的模型
const STORAGE_KEY = 'chat_selected_model';
const savedModel = localStorage.getItem(STORAGE_KEY);
if (savedModel) {
  currentModel.value = savedModel;
}

// 保存模型选择到 localStorage
watch(currentModel, (newModel) => {
  localStorage.setItem(STORAGE_KEY, newModel);
});

onMounted(async () => {
  // 获取模型列表
  try {
    const { data } = await modelsApi.getModels();
    models.value = data;
  } catch (error) {
    console.error('Failed to fetch models:', error);
  }

  await sessionStore.fetchSessions();
  const sessionId = route.params.sessionId as string;
  if (sessionId) {
    sessionStore.setCurrentSession(sessionId);
  } else if (sessionStore.sessions.length > 0) {
    const firstSession = sessionStore.sessions[0];
    router.replace(`/chat/${firstSession.session_id}`);
  } else {
    const newId = await sessionStore.createSession();
    router.replace(`/chat/${newId}`);
  }
});

watch(
  () => route.params.sessionId,
  (newId) => {
    if (newId) sessionStore.setCurrentSession(newId as string);
  }
);

async function handleNewSession() {
  const newId = await sessionStore.createSession();
  sessionStore.setCurrentSession(newId);
  router.push(`/chat/${newId}`);
}

async function handleDelete(message: Message) {
  if (!sessionStore.currentSessionId) return;
  await sessionStore.deleteMessage(sessionStore.currentSessionId, message.id);
}

async function handleEdit(message: Message) {
  editingMessageId.value = message.id;
  chatInputRef.value?.setInputText(message.content);
}

function handleCancelEdit() {
  editingMessageId.value = null;
  chatInputRef.value?.setInputText('');
}

async function handleRegenerate(message: Message) {
  if (!sessionStore.currentSessionId) return;
  await regenerate(sessionStore.currentSessionId, {
    message: message.content,
    enable_search: true,
    enable_code_exec: true,
    model: currentModel.value,
  });
}

async function handleSendMessage(
  message: string,
  attachments?: string[],
  enableSearch?: boolean,
  enableCodeExec?: boolean
) {
  if (!sessionStore.currentSessionId) return;
  if (editingMessageId.value != null) {
    await sessionStore.deleteMessage(sessionStore.currentSessionId, editingMessageId.value);
    editingMessageId.value = null;
  }
  await sendMessage(sessionStore.currentSessionId, {
    message,
    attachments_file_id: attachments,
    enable_search: enableSearch ?? true,
    enable_code_exec: enableCodeExec ?? true,
    model: currentModel.value,
  });
}
</script>