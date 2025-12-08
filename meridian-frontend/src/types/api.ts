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
}

export interface SendMessageResponse {
  message: Message;
  conversationId: string;
}

export interface GetConversationsResponse {
  conversations: Conversation[];
}

export interface GetMessagesResponse {
  messages: Message[];
  conversationId: string;
}

export interface CreateConversationResponse {
  conversation: Conversation;
}

export interface HealthCheckResponse {
  status: string;
  message?: string;
}

