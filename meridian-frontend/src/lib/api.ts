import type {
  ApiResponse,
  LoginResponse,
  SendMessageRequest,
  SendMessageResponse,
  GetConversationsResponse,
  GetMessagesResponse,
  CreateConversationResponse,
  HealthCheckResponse,
} from '@/types';
import { STORAGE_KEYS } from '@/lib/storage';

// Backend API URL - defaults to localhost:8000 for local development
const BACKEND_API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = BACKEND_API_URL) {
    this.baseUrl = baseUrl;
    if (typeof window !== 'undefined') {
      // Restore token from localStorage on initialization
      try {
        const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
        this.token = storedToken ? JSON.parse(storedToken) : null;
      } catch {
        this.token = null;
      }
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    // Always check for token from localStorage on each request
    // This ensures we have the latest token even if it was updated elsewhere
    if (typeof window !== 'undefined') {
      try {
        const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
        if (storedToken) {
          this.token = JSON.parse(storedToken);
        }
      } catch {
        // If parsing fails, token might be invalid - clear it
        this.token = null;
      }
    }

    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> | undefined),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
      console.log(`🔑 API Request with auth token: ${options.method || 'GET'} ${url}`);
    } else {
      console.warn(`⚠️ API Request WITHOUT auth token: ${options.method || 'GET'} ${url}`);
    }

    try {
      console.log(`🌐 API Request: ${options.method || 'GET'} ${url}`);
      const response = await fetch(url, {
        ...options,
        headers,
      });

      console.log(`🌐 API Response: ${response.status} ${response.statusText}`);
      
      const data = await response.json().catch((err) => {
        console.error('❌ Failed to parse JSON response:', err);
        return {};
      });

      if (!response.ok) {
        console.error(`❌ API Error Response:`, {
          status: response.status,
          error: data.error || data.message || data.detail,
          data,
        });
        
        // Handle 401 Unauthorized - clear token and redirect to login
        if (response.status === 401) {
          console.warn('⚠️ Unauthorized - clearing token');
          this.setToken(null);
          if (typeof window !== 'undefined') {
            // Clear user data as well
            localStorage.removeItem(STORAGE_KEYS.USER);
            // Optionally redirect to login page
            // window.location.href = '/';
          }
        }
        
        return {
          data: data as T,
          error: data.error || data.message || data.detail || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      console.log('✅ API Success Response:', {
        status: response.status,
        hasData: !!data,
      });

      return {
        data: data as T,
        status: response.status,
      };
    } catch (error) {
      console.error('❌ Network Error:', error);
      return {
        data: {} as T,
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      };
    }
  }

  setToken(token: string | null): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        // Store token using the same storage utility as AuthContext
        // Note: storage.set() uses JSON.stringify, so we need to match that
        localStorage.setItem(STORAGE_KEYS.TOKEN, JSON.stringify(token));
      } else {
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
      }
    }
  }

  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
    return this.request<HealthCheckResponse>('/api/health');
  }

  async logout(): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('/api/auth/logout', {
      method: 'POST',
    });
  }

  async loginWithGoogle(
    credential: string
  ): Promise<ApiResponse<LoginResponse>> {
    console.log('🔵 Step 3: API Client - Sending Google credential to backend');
    console.log('   Endpoint:', `${this.baseUrl}/api/auth/google`);
    console.log('   Credential length:', credential.length);
    
    const response = await this.request<LoginResponse>('/api/auth/google', {
      method: 'POST',
      body: JSON.stringify({ credential }),
    });
    
    console.log('🔵 Step 4: API Client - Received response');
    console.log('   Status:', response.status);
    console.log('   Has error:', !!response.error);
    console.log('   Has data:', !!response.data);
    if (response.error) {
      console.error('❌ API Error:', response.error);
    }
    if (response.data) {
      console.log('✅ Response data:', {
        hasUser: !!response.data.user,
        hasToken: !!response.data.token,
        userEmail: response.data.user?.email,
      });
    }
    
    return response;
  }

  /**
   * Send a chat message to a thread and receive an assistant response.
   * Uses the new backend API: POST /api/chat
   */
  async sendMessage(
    request: SendMessageRequest
  ): Promise<ApiResponse<SendMessageResponse>> {
    if (!request.conversationId && !request.thread_id) {
      return {
        data: {} as SendMessageResponse,
        error: 'Thread ID is required',
        status: 400,
      };
    }
    
    // Map conversationId to thread_id for backend API
    const backendRequest = {
      thread_id: request.conversationId || request.thread_id,
      message: request.message,
    };
    
    return this.request<SendMessageResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(backendRequest),
    });
  }

  /**
   * Get all threads (conversations).
   * Uses the new backend API: GET /api/threads
   */
  async getConversations(): Promise<ApiResponse<GetConversationsResponse>> {
    return this.request<GetConversationsResponse>('/api/threads');
  }

  /**
   * Get messages for a thread.
   * Uses the new backend API: GET /api/threads/{thread_id}/messages
   */
  async getMessages(
    conversationId: string
  ): Promise<ApiResponse<GetMessagesResponse>> {
    return this.request<GetMessagesResponse>(
      `/api/threads/${conversationId}/messages`
    );
  }

  /**
   * Create a new thread (conversation).
   * Uses the new backend API: POST /api/threads
   */
  async createConversation(
    title?: string
  ): Promise<ApiResponse<CreateConversationResponse>> {
    return this.request<CreateConversationResponse>('/api/threads', {
      method: 'POST',
      body: JSON.stringify({ title: title || null }),
    });
  }

  /**
   * Delete a thread (conversation).
   * Uses the new backend API: DELETE /api/threads/{thread_id}
   */
  async deleteConversation(
    conversationId: string
  ): Promise<ApiResponse<{ success: boolean; thread_id: string }>> {
    return this.request<{ success: boolean; thread_id: string }>(
      `/api/threads/${conversationId}`,
      {
        method: 'DELETE',
      }
    );
  }
}

export const apiClient = new ApiClient(BACKEND_API_URL);

