import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { apiClient } from '@/api/client';
import type { User } from '@/types';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'));
  const user = ref<User | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  // 设置 token 并持久化
  function setToken(newToken: string) {
    token.value = newToken;
    localStorage.setItem('token', newToken);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
  }

  // 调用 /me 获取用户信息
  async function fetchUser() {
    if (!token.value) return;
    try {
      const { data } = await apiClient.get<User>('/me');
      user.value = data;
    } catch (error) {
      // token 无效，清除状态
      logout();
    }
  }

  async function login(username: string, password: string) {
    const { data } = await apiClient.post('/login', { username, password });
    setToken(data.access_token);
    await fetchUser();
  }

  async function register(username: string, password: string) {
    const { data } = await apiClient.post('/register', { username, password });
    setToken(data.access_token);
    await fetchUser();
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem('token');
    delete apiClient.defaults.headers.common['Authorization'];
  }

  // 初始化时尝试获取用户信息
  if (token.value) {
    fetchUser();
  }

  return { token, user, isAuthenticated, login, register, logout, fetchUser };
});