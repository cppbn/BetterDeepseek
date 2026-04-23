import { apiClient } from './client';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  login: (data: LoginRequest) => apiClient.post<TokenResponse>('/login', data),
  register: (data: RegisterRequest) => apiClient.post<TokenResponse>('/register', data),
};