import { apiClient } from './client';
import type { Message } from '@/types';

export const messagesApi = {
  list: (sessionId: string) => apiClient.get<Message[]>(`/sessions/${sessionId}/messages`),
  deleteAll: (sessionId: string) => apiClient.delete(`/sessions/${sessionId}/messages`),
  deleteOne: (sessionId: string, messageId: number) =>
    apiClient.delete(`/sessions/${sessionId}/messages?message_id=${messageId}`),
};