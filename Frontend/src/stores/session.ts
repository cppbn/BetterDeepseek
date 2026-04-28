import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiClient } from '@/api/client';
import { type Session, type Message, type FileInfo } from '@/types';

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([]);
  const currentSessionId = ref<string | null>(null);
  const messagesMap = ref<Record<string, Message[]>>({});
  const isLoadingMessages = ref(false);

  const currentMessages = computed(() => {
    if (!currentSessionId.value) return [];
    return messagesMap.value[currentSessionId.value] || [];
  });

  function ensureSessionMessages(sessionId: string) {
    if (!messagesMap.value[sessionId]) {
      messagesMap.value[sessionId] = [];
    }
  }

  function addMessageToSession(sessionId: string, message: Message) {
    ensureSessionMessages(sessionId);
    const msgs = messagesMap.value[sessionId]!;
    message.seq = (msgs.at(-1)?.seq ?? -1) + 1;
    msgs.push(message);
  }

  function updateLastMessageInSession(
    sessionId: string,
    updater: (msg: Message) => void
  ) {
    const msgs = messagesMap.value[sessionId];
    if (msgs && msgs.length > 0) {
      updater(msgs[msgs.length - 1]);
    }
  }

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
    delete messagesMap.value[sessionId];
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = null;
    }
    await fetchSessions();
  }

  async function fetchMessages(sessionId: string) {
    isLoadingMessages.value = true;
    try {
      const { data } = await apiClient.get<Message[]>(
        `/sessions/${sessionId}/messages`
      );
      messagesMap.value[sessionId] = data;

      await Promise.all(
        data
          .filter(
            (m) =>
              m.role === 'user' ||
              (m.role === 'assistant' && m.type === 'tool_call')
          )
          .map(async (message) => {
            const { data: attachments } = await apiClient.get<FileInfo[]>(
              `/sessions/${sessionId}/messages/${message.id}/attachments`
            );
            message.attachments = attachments;
            message.attachments_file_id = attachments.map((f) => f.file_id);
          })
      );
    } finally {
      isLoadingMessages.value = false;
    }
  }

  async function deleteMessage(sessionId: string, messageId: number, opts?: { keepUserFiles?: boolean }) {
    const params = new URLSearchParams();
    if (opts?.keepUserFiles) params.set('keep_user_files', 'true');
    const url = `/sessions/${sessionId}/messages/${messageId}${params.toString() ? '?' + params.toString() : ''}`;
    await apiClient.delete(url);
    await fetchMessages(sessionId);
  }

  function setCurrentSession(sessionId: string) {
    if (currentSessionId.value === sessionId) return;
    currentSessionId.value = sessionId;
    if (!messagesMap.value[sessionId]) {
      fetchMessages(sessionId);
    }
  }

  function updateSessionTitle(sessionId: string, title: string) {
    const session = sessions.value.find((s) => s.session_id === sessionId);
    if (session) {
      session.title = title;
    }
  }

  async function syncAfterStream(sessionId: string) {
    try {
      const { data } = await apiClient.get<Message[]>(
        `/sessions/${sessionId}/messages`
      );
      const localMsgs = messagesMap.value[sessionId];
      if (!localMsgs || localMsgs.length === 0) {
        messagesMap.value[sessionId] = data;
        return;
      }
      const serverBySeq = new Map<number, Message>();
      for (const m of data) {
        serverBySeq.set(m.seq, m);
      }
      for (const local of localMsgs) {
        const server = serverBySeq.get(local.seq);
        if (server && local.id < 0) {
          local.id = server.id;
        }
      }
    } catch {
      // silent — messages are already displayed from streaming
    }
  }

  function removeMessagesFromIndex(sessionId: string, fromIdx: number) {
    const msgs = messagesMap.value[sessionId];
    if (msgs) {
      messagesMap.value[sessionId] = msgs.filter((m) => m.idx < fromIdx);
    }
  }

  return {
    sessions,
    currentSessionId,
    isLoadingMessages,
    currentMessages,
    messagesMap,
    fetchSessions,
    createSession,
    deleteSession,
    fetchMessages,
    deleteMessage,
    setCurrentSession,
    addMessageToSession,
    updateLastMessageInSession,
    updateSessionTitle,
    syncAfterStream,
    removeMessagesFromIndex,
  };
});