import { ref } from 'vue';
import { useSessionStore } from '@/stores/session';
import { streamChat } from '@/api/stream';
import type { Message, ChatRequest, StreamEvent } from '@/types';
import { filesApi } from '@/api/files';
export function useChatStream() {
  const sessionStore = useSessionStore();
  const isStreaming = ref(false);

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

    isStreaming.value = true;

    try {
      const generator = streamChat(sessionId, {
        message: request.message,
        attachments_file_id: request.attachments_file_id,
        enable_search: request.enable_search ?? true,
        enable_code_exec: request.enable_code_exec ?? true,
        model: request.model,
      });

      for await (const event of generator) {
        handleStreamEvent(event);
      }
    } catch (error) {
      console.error('Stream error:', error);
      sessionStore.updateLastMessage((msg) => {
        msg.content = '发生错误，请重试。';
        msg.isStreaming = false;
      });
    } finally {
      isStreaming.value = false;
      // 标记流式结束
      sessionStore.updateLastMessage((msg) => {
        msg.isStreaming = false;
      });
      // 注意：不再调用 fetchMessages，避免覆盖本地已累积的完整内容
      // 如果后端要求同步，可以在后台静默拉取，但不影响当前显示
      // await sessionStore.fetchMessages(sessionId);
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

  return { sendMessage, isStreaming };
}