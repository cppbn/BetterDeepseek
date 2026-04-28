import { apiClient } from './client';
import type { FileInfo } from '@/types';

function generateUUID(): string {
  return crypto.randomUUID();
}

export const filesApi = {
  // 原有上传
  upload: (sessionId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<FileInfo>(`/sessions/${sessionId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // 分块上传（用于大文件，绕过 Cloudflare 请求体大小限制）
  uploadLarge: async (
    sessionId: string,
    file: File,
    onProgress?: (pct: number) => void,
    chunkSize: number = 256 * 1024,
  ) => {
    const fileId = generateUUID();
    const totalChunks = Math.ceil(file.size / chunkSize);

    let lastData: FileInfo | null = null;

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const blob = file.slice(start, end);

      const formData = new FormData();
      formData.append('file_id', fileId);
      formData.append('chunk_index', String(i));
      formData.append('total_chunks', String(totalChunks));
      formData.append('original_filename', file.name);
      formData.append('mime_type', file.type || 'application/octet-stream');
      formData.append('chunk', blob, file.name);

      const { data } = await apiClient.post<FileInfo>(
        `/sessions/${sessionId}/files/chunked`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );

      if (i === totalChunks - 1) {
        lastData = data;
      }

      onProgress?.(Math.round(((i + 1) / totalChunks) * 100));
    }

    return { data: lastData! };
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