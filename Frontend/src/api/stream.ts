import { apiClient } from './client';
import type { ChatRequest, StreamEvent } from '@/types';

export async function* streamChat(
  sessionId: string,
  request: ChatRequest & { signal?: AbortSignal }
): AsyncGenerator<StreamEvent> {
  const response = await fetch(
    `${apiClient.defaults.baseURL}/sessions/${sessionId}/chat/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(request),
      signal: request.signal,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (dataStr === '[DONE]') return;
          try {
            const event = JSON.parse(dataStr) as StreamEvent;
            yield event;
          } catch (e) {
            console.warn('Failed to parse SSE:', dataStr);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}