import type { Message, Conversation, User } from './index';

export interface ApiResponse<T> {
  data: T;
  error?: string;
  status: number;
}

export interface LoginResponse {
  user: User;
  token: string;
}

export interface SendMessageRequest {
  message: string;
  conversationId?: string;
  thread_id?: string; // Backend uses thread_id
}

export interface SendMessageResponse {
  thread_id: string;
  message_id: string;
  assistant_message_id: string | null;
  response: string | null;
  use_streaming?: boolean;
  intent?: string;
  workflow?: string;
  agents?: string[];
}

export interface GetConversationsResponse {
  threads: Array<{
    thread_id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
    user_id: string | null;
    message_count?: number;
    last_message_at?: string | null;
  }>;
}

export interface GetMessagesResponse {
  thread_id: string;
  messages: Array<{
    message_id: string;
    thread_id: string;
    role: string;
    content: string;
    timestamp: string;
    metadata: any;
  }>;
}

export interface CreateConversationResponse {
  thread_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  message_count?: number;
  last_message_at?: string | null;
}

export interface HealthCheckResponse {
  status: string;
  message?: string;
}

