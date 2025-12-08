import type {
  ApiResponse,
  LoginResponse,
  SendMessageRequest,
  SendMessageResponse,
  GetConversationsResponse,
  GetMessagesResponse,
  CreateConversationResponse,
  HealthCheckResponse,
  LoginCredentials,
  RegisterCredentials,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('meridian-token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> | undefined),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        return {
          data: data as T,
          error: data.error || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      return {
        data: data as T,
        status: response.status,
      };
    } catch (error) {
      return {
        data: {} as T,
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  setToken(token: string | null): void {
    this.token = token;
    if (token && typeof window !== 'undefined') {
      localStorage.setItem('meridian-token', token);
    } else if (typeof window !== 'undefined') {
      localStorage.removeItem('meridian-token');
    }
  }

  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
    return this.request<HealthCheckResponse>('/api/health');
  }

  async login(
    credentials: LoginCredentials
  ): Promise<ApiResponse<LoginResponse>> {
    return this.request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async register(
    credentials: RegisterCredentials
  ): Promise<ApiResponse<LoginResponse>> {
    return this.request<LoginResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async logout(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('/api/auth/logout', {
      method: 'POST',
    });
  }

  async sendMessage(
    request: SendMessageRequest
  ): Promise<ApiResponse<SendMessageResponse>> {
    return this.request<SendMessageResponse>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getConversations(): Promise<ApiResponse<GetConversationsResponse>> {
    return this.request<GetConversationsResponse>('/api/chat/conversations');
  }

  async getMessages(
    conversationId: string
  ): Promise<ApiResponse<GetMessagesResponse>> {
    return this.request<GetMessagesResponse>(
      `/api/chat/conversations/${conversationId}/messages`
    );
  }

  async createConversation(
    title?: string
  ): Promise<ApiResponse<CreateConversationResponse>> {
    return this.request<CreateConversationResponse>('/api/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  }

  async deleteConversation(
    conversationId: string
  ): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(
      `/api/chat/conversations/${conversationId}`,
      {
        method: 'DELETE',
      }
    );
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

