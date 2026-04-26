import { ref } from 'vue';
import { useSessionStore } from '@/stores/session';
import { streamChat } from '@/api/stream';
import type { Message, ChatRequest, StreamEvent } from '@/types';
import { filesApi } from '@/api/files';
export function useChatStream() {
  const sessionStore = useSessionStore();
  const isStreaming = ref(false);
  const abortController = ref<AbortController | null>(null);
  let _tempIdCounter = -1;

  async function sendMessage(sessionId: string, request: ChatRequest) {
    if (isStreaming.value) return;

    const streamSessionId = sessionId;

    const msgs = sessionStore.messagesMap[streamSessionId] || [];
    const lastMsgIdx = msgs.at(-1)?.idx ?? -1;
    const userMsgIdx = lastMsgIdx + 1;
    const turnIdx = userMsgIdx + 1;

    const userMsg: Message = {
      id: _tempIdCounter--,
      seq: 0,
      idx: userMsgIdx,
      role: 'user',
      type: 'message',
      content: request.message,
      created_at: new Date().toISOString(),
      attachments_file_id: request.attachments_file_id,
    };
    sessionStore.addMessageToSession(streamSessionId, userMsg);

    const assistantMsg: Message = {
      id: _tempIdCounter--,
      seq: 0,
      idx: turnIdx,
      role: 'assistant',
      type: 'reasoning',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
    };
    sessionStore.addMessageToSession(streamSessionId, assistantMsg);

    const controller = new AbortController();
    abortController.value = controller;
    isStreaming.value = true;

    try {
      const generator = streamChat(streamSessionId, {
        message: request.message,
        attachments_file_id: request.attachments_file_id,
        enable_search: request.enable_search ?? true,
        enable_code_exec: request.enable_code_exec ?? true,
        model: request.model,
        signal: controller.signal,
      });

      for await (const event of generator) {
        handleStreamEvent(streamSessionId, turnIdx, event);
      }
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
          if (!msg.content.endsWith('（已停止）')) {
            msg.content += '（已停止）';
          }
        });
      } else {
        console.error('Stream error:', error);
        sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
          msg.content = '发生错误，请重试。';
          msg.isStreaming = false;
        });
      }
    } finally {
      sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
        msg.isStreaming = false;
      });
      isStreaming.value = false;
      await sessionStore.syncAfterStream(streamSessionId);
    }
  }

  function handleStreamEvent(streamSessionId: string, turnIdx: number, event: StreamEvent) {
    switch (event.type) {
      case 'content':
        sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
          if (msg.type === 'message') {
            msg.content += event.content;
          } else {
            sessionStore.addMessageToSession(streamSessionId, {
              id: _tempIdCounter--,
              seq: 0,
              idx: msg.idx,
              role: 'assistant',
              type: 'message',
              content: event.content,
              created_at: new Date().toISOString(),
            });
          }
        });
        break;
      case 'reasoning_content':
        sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
          if (msg.type === 'reasoning') {
            msg.content += event.content;
          } else {
            sessionStore.addMessageToSession(streamSessionId, {
              id: _tempIdCounter--,
              seq: 0,
              idx: msg.idx,
              role: 'assistant',
              type: 'reasoning',
              content: event.content,
              created_at: new Date().toISOString(),
            });
          }
        });
        break;
      case 'tool_call':
        sessionStore.addMessageToSession(streamSessionId, {
          id: _tempIdCounter--,
          seq: 0,
          idx: turnIdx,
          role: 'assistant',
          type: 'tool_call',
          content: `调用工具: ${event.content.name}`,
          created_at: new Date().toISOString(),
          toolCallData: event.content,
        });
        break;
      case 'tool_result':
        sessionStore.addMessageToSession(streamSessionId, {
          id: _tempIdCounter--,
          seq: 0,
          idx: turnIdx,
          role: 'tool',
          type: 'tool_result',
          content: event.content,
          created_at: new Date().toISOString(),
        });
        break;
      case 'file':
        const fileId = event.content.file_id;
        const fileMsg: Message = {
          id: _tempIdCounter--,
          seq: 0,
          idx: turnIdx,
          role: 'tool',
          type: 'tool_result',
          content: `文件已导出: ${fileId}`,
          created_at: new Date().toISOString(),
          attachments_file_id: [fileId],
        };
        filesApi.getFileInfo(streamSessionId, fileId).then(({ data }) => {
          fileMsg.attachments = [data];
        });
        sessionStore.addMessageToSession(streamSessionId, fileMsg);
        break;
      case 'error':
        sessionStore.updateLastMessageInSession(streamSessionId, (msg) => {
          msg.content += `\n错误: ${event.content}`;
          msg.isStreaming = false;
        });
        break;
      case 'title':
        sessionStore.updateSessionTitle(streamSessionId, event.content);
        break;
    }
  }

  function stop() {
    if (abortController.value) {
      abortController.value.abort();
    }
  }

  async function regenerate(sessionId: string, request: ChatRequest) {
    const msgs = sessionStore.messagesMap[sessionId] || [];
    if (msgs.length === 0) return;
    const lastUserMsg = [...msgs].reverse().find((m) => m.role === 'user');
    if (!lastUserMsg) return;
    await sessionStore.deleteMessage(sessionId, lastUserMsg.id);
    await sendMessage(sessionId, { ...request, message: lastUserMsg.content });
  }

  return { sendMessage, isStreaming, stop, regenerate };
}
