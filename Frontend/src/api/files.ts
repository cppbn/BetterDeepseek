import { apiClient } from './client';
import type { FileInfo } from '@/types';

export const filesApi = {
  // 原有上传
  upload: (sessionId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<FileInfo>(`/sessions/${sessionId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // 获取文件元信息
  getFileInfo: (sessionId: string, fileId: string) =>
    apiClient.get<FileInfo>(`/sessions/${sessionId}/files/${fileId}/metadata`),

  // 获取文件 Blob（不自动下载）
  getFileBlob: (sessionId: string, fileId: string) =>
    apiClient.get(`/sessions/${sessionId}/files/${fileId}`, {
      responseType: 'blob',
    }),

  // 下载文件（使用 getFileBlob 复用）
  download: async (sessionId: string, fileId: string, fileName?: string) => {
    const response = await filesApi.getFileBlob(sessionId, fileId);
    const url = window.URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName || fileId);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // 预览文件（新窗口打开）
  preview: async (sessionId: string, fileId: string) => {
    const response = await apiClient.get(`/sessions/${sessionId}/files/${fileId}`, {
      responseType: 'blob',
    });
    // 直接使用 response.data，保留后端返回的 Content-Type
    const url = window.URL.createObjectURL(response.data);
    window.open(url, '_blank');
    // 注意：由于新窗口独立，无法立即 revoke，可延迟一段时间或交由浏览器回收
  },

  // 原有下载 URL（保留，可用于直接链接，但需注意认证问题）
  downloadUrl: (sessionId: string, fileId: string) =>
    `${apiClient.defaults.baseURL}/sessions/${sessionId}/files/${fileId}`,
};