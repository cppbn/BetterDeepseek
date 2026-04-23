import { apiClient } from './client';
import type { ModelsResponse } from '@/types';

export const modelsApi = {
  getModels() {
    return apiClient.get<ModelsResponse>('/models');
  },
};