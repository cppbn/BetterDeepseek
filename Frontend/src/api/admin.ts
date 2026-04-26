import { apiClient } from './client';
import type { ModelInfo } from '@/types';

export interface ModelConfig {
  key: string;
  provider: string;
  model: string;
  thinking: boolean;
  accept_image: boolean;
  accept_audio: boolean;
  is_default: boolean;
  category: string;
}

export interface UserRecord {
  id: number;
  username: string;
  created_at: string;
}

export interface TokenUsageSummary {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_requests: number;
}

export interface TokenUsageByModel {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  requests: number;
}

export interface TokenUsageByUser {
  username: string;
  prompt_tokens: number;
  completion_tokens: number;
  requests: number;
}

export interface TokenUsage {
  summary: TokenUsageSummary;
  by_model: TokenUsageByModel[];
  by_user: TokenUsageByUser[];
}

export interface EnvConfig {
  key: string;
  value: string;
}

function adminHeaders() {
  const key = localStorage.getItem('admin_key') || '';
  return { 'X-Admin-Key': key };
}

export const adminApi = {
  // Verify key
  verify(key: string) {
    return apiClient.post<{ valid: boolean }>('/admin/verify', { key });
  },

  // Env / Prompts
  getConfigs() {
    return apiClient.get<EnvConfig[]>('/admin/env', { headers: adminHeaders() });
  },
  getConfig(key: string) {
    return apiClient.get<{ key: string; value: string }>(`/admin/env/${key}`, { headers: adminHeaders() });
  },
  setConfig(key: string, value: string) {
    return apiClient.post(`/admin/env/${key}`, { value }, { headers: adminHeaders() });
  },

  // Models
  getModels() {
    return apiClient.get<ModelConfig[]>('/admin/models', { headers: adminHeaders() });
  },
  getModel(key: string) {
    return apiClient.get<ModelConfig>(`/admin/models/${key}`, { headers: adminHeaders() });
  },
  upsertModel(key: string, data: ModelConfig) {
    return apiClient.put(`/admin/models/${key}`, data, { headers: adminHeaders() });
  },
  deleteModel(key: string) {
    return apiClient.delete(`/admin/models/${key}`, { headers: adminHeaders() });
  },

  // Users
  getUsers() {
    return apiClient.get<UserRecord[]>('/admin/users', { headers: adminHeaders() });
  },
  deleteUser(userId: number) {
    return apiClient.delete(`/admin/users/${userId}`, { headers: adminHeaders() });
  },

  // Token Usage
  getTokenUsage() {
    return apiClient.get<TokenUsage>('/admin/token-usage', { headers: adminHeaders() });
  },
};
