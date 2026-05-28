import { apiClient } from './client';

export interface DevSettings {
  system_prompt_default: string | null;
  system_prompt_with_code_exec: string | null;
  sandbox_network_disabled: boolean;
  sandbox_idle_timeout: number;
}

export const devApi = {
  getSettings() {
    return apiClient.get<DevSettings>('/dev/settings');
  },
  updateSettings(data: Partial<DevSettings>) {
    return apiClient.put('/dev/settings', data);
  },
};
