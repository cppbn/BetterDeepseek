import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiClient } from '@/api/client';
import { type Session, type Message, type FileInfo } from '@/types';

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([]);
  const currentSessionId = ref<string | null>(null);
  const messages = ref<Message[]>([]);
  const isLoadingMessages = ref(false);

  async function fetchSessions() {
    const { data } = await apiClient.get<Session[]>('/sessions');
    sessions.value = data;
  }

  async function createSession() {
    const { data } = await apiClient.post<{ session_id: string }>('/sessions');
    await fetchSessions();
    return data.session_id;
  }

  async function deleteSession(sessionId: string) {
    await apiClient.delete(`/sessions/${sessionId}`);
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null;
      messages.value = [];
    }
    await fetchSessions();
  }

  async function fetchMessages(sessionId: string) {
    isLoadingMessages.value = true;
    try {
      const { data } = await apiClient.get<Message[]>(`/sessions/${sessionId}/messages`);
      messages.value = data;
      await Promise.all(
        messages.value
            .filter(m => m.role === 'user' || (m.role === 'assistant' && m.type === 'tool_call'))
            .map(async (message) => {
                const { data } = await apiClient.get<FileInfo[]>(`/sessions/${sessionId}/messages/${message.id}/attachments`);
                message.attachments = data;
                message.attachments_file_id = message.attachments.map(f => f.file_id);
            })
);
    } finally {
      isLoadingMessages.value = false;
    }
  }

  async function deleteMessage(sessionId: string, messageId: number) {
    await apiClient.delete(`/sessions/${sessionId}/messages/${messageId}`);
    await fetchMessages(sessionId);
  }

  function setCurrentSession(sessionId: string) {
    currentSessionId.value = sessionId;
    fetchMessages(sessionId);
  }

  function addMessage(message: Message) {
    messages.value.push(message);
  }

  function updateLastMessage(updater: (msg: Message) => void) {
    if (messages.value.length > 0) {
      updater(messages.value[messages.value.length - 1]);
    }
  }

  return {
    sessions,
    currentSessionId,
    messages,
    isLoadingMessages,
    fetchSessions,
    createSession,
    deleteSession,
    fetchMessages,
    setCurrentSession,
    addMessage,
    updateLastMessage,
  };
});