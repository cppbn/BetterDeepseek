import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiClient } from '@/api/client';
import { type Session, type Message, type FileInfo, type ReasoningStep } from '@/types';

function mergeReasoningGroup(group: Message[]): Message {
  const base = group[0]!;
  const steps: ReasoningStep[] = [];

  for (const msg of group) {
    if (msg.type === 'reasoning') {
      const lastStep = steps.at(-1);
      if (lastStep && lastStep.type === 'thinking') {
        lastStep.content += msg.content;
      } else {
        steps.push({ type: 'thinking', content: msg.content });
      }
    } else if (msg.type === 'tool_call') {
      let toolName = '';
      let toolArgs: any = {};
      try {
        if (msg.toolCallData) {
          toolName = msg.toolCallData.name;
          toolArgs = msg.toolCallData.args;
        } else {
          const parsed = JSON.parse(msg.content);
          toolName = parsed.name || '';
          toolArgs = parsed.args || {};
        }
      } catch {
        toolName = msg.content;
      }
      steps.push({
        type: 'tool_call',
        content: toolName,
        toolName,
        toolArgs,
        toolResult: '',
      });
    } else if (msg.type === 'tool_result') {
      let resultContent = msg.content;
      try {
        const parsed = JSON.parse(msg.content);
        if (parsed && typeof parsed === 'object' && typeof parsed.content === 'string') {
          resultContent = parsed.content;
        }
      } catch { /* not JSON wrapper, use as-is */ }
      for (let j = steps.length - 1; j >= 0; j--) {
        const step = steps[j];
        if (step && step.type === 'tool_call' && !step.toolResult) {
          step.toolResult = resultContent;
          break;
        }
      }
    }
  }

  const thinkingContent = steps
    .filter((s) => s.type === 'thinking')
    .map((s) => s.content)
    .join('');

  return {
    id: base.id,
    seq: base.seq,
    idx: base.idx,
    created_at: base.created_at,
    type: 'reasoning' as const,
    role: 'assistant' as const,
    content: thinkingContent,
    reasoningSteps: steps,
    isStreaming: false,
    attachments_file_id: base.attachments_file_id,
    attachments: base.attachments,
  };
}

function mergeReasoningMessages(messages: Message[]): Message[] {
  const result: Message[] = [];
  let i = 0;
  while (i < messages.length) {
    const msg = messages[i]!;
    if (
      msg.type === 'reasoning' ||
      msg.type === 'tool_call' ||
      msg.type === 'tool_result'
    ) {
      const groupStart = i;
      while (
        i < messages.length &&
        (messages[i]!.type === 'reasoning' ||
          messages[i]!.type === 'tool_call' ||
          messages[i]!.type === 'tool_result')
      ) {
        i++;
      }
      const group = messages.slice(groupStart, i);
      result.push(mergeReasoningGroup(group));
    } else {
      result.push(msg);
      i++;
    }
  }
  return result;
}

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
      updater(msgs[msgs.length - 1]!);
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
      messagesMap.value[sessionId] = mergeReasoningMessages(data);

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
      messagesMap.value[sessionId] = mergeReasoningMessages(data);
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