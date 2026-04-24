import { ref } from 'vue';
import { useSessionStore } from '@/stores/session';
import { streamChat } from '@/api/stream';
import type { Message, ChatRequest, StreamEvent } from '@/types';
import { filesApi } from '@/api/files';
export function useChatStream() {
  const sessionStore = useSessionStore();
  const isStreaming = ref(false);
  const abortController = ref<AbortController | null>(null);

  async function sendMessage(sessionId: string, request: ChatRequest) {
    if (isStreaming.value) return;

    // 用户消息
    const userMsg: Message = {
      id: Date.now(),
      idx: sessionStore.messages.length > 0 ? sessionStore.messages[sessionStore.messages.length - 1].idx + 1 : 0,
      role: 'user',
      type: 'message',
      content: request.message,
      created_at: new Date().toISOString(),
      attachments_file_id: request.attachments_file_id,
    };
    sessionStore.addMessage(userMsg);

    // 占位助手消息
    const assistantMsg: Message = {
      id: Date.now() + 1,
      idx: userMsg.idx + 1, // 确保 idx 递增
      role: 'assistant',
      type: 'reasoning',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
    };
    sessionStore.addMessage(assistantMsg);

    const controller = new AbortController();
    abortController.value = controller;
    isStreaming.value = true;

    try {
      const generator = streamChat(sessionId, {
        message: request.message,
        attachments_file_id: request.attachments_file_id,
        enable_search: request.enable_search ?? true,
        enable_code_exec: request.enable_code_exec ?? true,
        model: request.model,
        signal: controller.signal,
      });

      for await (const event of generator) {
        handleStreamEvent(event);
      }
    } catch (error) {
      if (error?.name === 'AbortError') {
        // 用户主动取消，追加提示（可选）
        sessionStore.updateLastMessage((msg) => {
          if (!msg.content.endsWith('（已停止）')) {
            msg.content += '（已停止）';
          }
        });
      } else {
        console.error('Stream error:', error);
        sessionStore.updateLastMessage((msg) => {
          msg.content = '发生错误，请重试。';
          msg.isStreaming = false;
        });
      }
    } finally {
      isStreaming.value = false;
      // 标记流式结束
      sessionStore.updateLastMessage((msg) => {
        msg.isStreaming = false;
      });
    }
  }

  function handleStreamEvent(event: StreamEvent) {
    switch (event.type) {
      case 'content':
        sessionStore.updateLastMessage((msg) => {
          if(msg.type === "message"){
            msg.content += event.content;
          }
          else{
            sessionStore.addMessage({
              id: Date.now(),
              idx: sessionStore.messages[sessionStore.messages.length - 1].idx,
              role: 'assistant',
              type: 'message',
              content: event.content,
              created_at: new Date().toISOString(),
            });
          }
        });
        break;
      case 'reasoning_content':
        sessionStore.updateLastMessage((msg) => {
          if(msg.type === "reasoning"){
            msg.content += event.content;
          }
          else{
            sessionStore.addMessage({
              id: Date.now(),
              idx: sessionStore.messages[sessionStore.messages.length - 1].idx,
              role: 'assistant',
              type: 'reasoning',
              content: event.content,
              created_at: new Date().toISOString(),
            });
          }
        });
        break;
      case 'tool_call':
        sessionStore.addMessage({
          id: Date.now(),
          idx: sessionStore.messages[sessionStore.messages.length - 1].idx,
          role: 'assistant',
          type: 'tool_call',
          content: `调用工具: ${event.content.name}`,
          created_at: new Date().toISOString(),
          toolCallData: event.content,
        });
        break;
      case 'tool_result':
        sessionStore.addMessage({
          id: Date.now(),
          idx: sessionStore.messages[sessionStore.messages.length - 1].idx,
          role: 'tool',
          type: 'tool_result',
          content: event.content,
          created_at: new Date().toISOString(),
        });
        break;
      case 'file':
        const fileId = event.content.file_id;
        const fileMsg: Message = {
          id: Date.now(),
          idx: sessionStore.messages[sessionStore.messages.length - 1].idx,
          role: 'tool',
          type: 'tool_result',
          content: `文件已导出: ${fileId}`,
          created_at: new Date().toISOString(),
          attachments_file_id: [fileId],
        };
        // 异步获取文件信息并更新
        filesApi.getFileInfo(sessionStore.currentSessionId, fileId).then(({ data }) => {
          fileMsg.attachments = [data];
        });
  sessionStore.addMessage(fileMsg);
  break;
      case 'error':
        sessionStore.updateLastMessage((msg) => {
          msg.content += `\n错误: ${event.content}`;
          msg.isStreaming = false;
        });
        break;
    }
  }

  function stop() {
    if (abortController.value) {
      abortController.value.abort();
    }
  }

  return { sendMessage, isStreaming, stop };
}