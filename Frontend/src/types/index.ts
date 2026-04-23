import type { list } from "postcss";

export interface User {
  id: number;
  username: string;
}

export interface Session {
  session_id: string;
  created_at: string;
}

export interface Message {
  id: number;
  idx: number;
  role: 'user' | 'assistant' | 'tool';
  type: 'message' | 'reasoning' | 'tool_call' | 'tool_result';
  content: string;
  created_at: string;
  isStreaming?: boolean;
  toolCallData?: any;
  attachments_file_id?: string[];
  attachments?: FileInfo[];
}

export interface FileInfo {
  file_id: string;
  original_filename: string;
  file_size: number;
  mime_type?: string;
}

export interface ChatRequest {
  message: string;
  attachments_file_id?: string[];
  model?: string;
  enable_search?: boolean;
  enable_code_exec?: boolean;
}

export interface StreamEvent {
  type: 'content' | 'reasoning_content' | 'tool_call' | 'tool_result' | 'file' | 'error';
  content: any;
}

export interface ModelInfo {
  provider: string;
  model: string;
  thinking: boolean;
  accept_image: boolean;
  accept_audio: boolean;
}

export interface ModelsResponse {
  [key: string]: ModelInfo;
}