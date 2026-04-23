import { apiClient } from './client';
import type { Session } from '@/types';

export const sessionsApi = {
  list: () => apiClient.get<Session[]>('/sessions'),
  create: () => apiClient.post<{ session_id: string }>('/sessions'),
  delete: (sessionId: string) => apiClient.delete(`/sessions/${sessionId}`),
};