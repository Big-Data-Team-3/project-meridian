import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from './api';
import { STORAGE_KEYS } from './storage';

// Mock fetch globally
global.fetch = vi.fn();

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('setToken', () => {
    it('stores token in localStorage', () => {
      apiClient.setToken('test-token-123');
      const stored = localStorage.getItem(STORAGE_KEYS.TOKEN);
      expect(stored).toBe(JSON.stringify('test-token-123'));
    });

    it('removes token when set to null', () => {
      apiClient.setToken('test-token');
      apiClient.setToken(null);
      expect(localStorage.getItem(STORAGE_KEYS.TOKEN)).toBeNull();
    });
  });

  describe('healthCheck', () => {
    it('makes GET request to /api/health', async () => {
      const mockResponse = { status: 'ok' };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.healthCheck();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/health'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result.data).toEqual(mockResponse);
      expect(result.error).toBeUndefined();
    });
  });

  describe('loginWithGoogle', () => {
    it('sends POST request with credential', async () => {
      const mockResponse = {
        token: 'auth-token',
        user: { id: '1', email: 'test@example.com' },
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.loginWithGoogle('google-credential');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/auth/google'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ credential: 'google-credential' }),
        })
      );
      expect(result.data).toEqual(mockResponse);
    });
  });

  describe('sendMessage', () => {
    it('sends POST request with message and thread_id', async () => {
      const mockResponse = {
        thread_id: 'thread-1',
        response: 'Assistant response',
        use_streaming: false,
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.sendMessage({
        conversationId: 'thread-1',
        message: 'User message',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/chat'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            thread_id: 'thread-1',
            message: 'User message',
          }),
        })
      );
      expect(result.data).toEqual(mockResponse);
    });

    it('returns error when conversationId is missing', async () => {
      const result = await apiClient.sendMessage({
        conversationId: '',
        message: 'Test',
      });

      expect(result.error).toBe('Thread ID is required');
      expect(result.status).toBe(400);
    });
  });

  describe('getConversations', () => {
    it('makes GET request to /api/threads', async () => {
      const mockResponse = {
        threads: [
          { thread_id: '1', title: 'Thread 1', created_at: '2024-01-01' },
        ],
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.getConversations();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/threads'),
        expect.any(Object)
      );
      expect(result.data).toEqual(mockResponse);
    });
  });

  describe('getMessages', () => {
    it('makes GET request to /api/threads/{id}/messages', async () => {
      const mockResponse = {
        thread_id: 'thread-1',
        messages: [
          {
            message_id: 'msg-1',
            role: 'user',
            content: 'Hello',
            timestamp: '2024-01-01T10:00:00Z',
          },
        ],
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.getMessages('thread-1');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/threads/thread-1/messages'),
        expect.any(Object)
      );
      expect(result.data).toEqual(mockResponse);
    });
  });

  describe('createConversation', () => {
    it('sends POST request to create thread', async () => {
      const mockResponse = {
        thread_id: 'new-thread-1',
        title: 'New Thread',
      };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.createConversation('New Thread');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/threads'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ title: 'New Thread' }),
        })
      );
      expect(result.data).toEqual(mockResponse);
    });
  });

  describe('deleteConversation', () => {
    it('sends DELETE request', async () => {
      const mockResponse = { success: true, thread_id: 'thread-1' };
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await apiClient.deleteConversation('thread-1');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/threads/thread-1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
      expect(result.data).toEqual(mockResponse);
    });
  });

  describe('error handling', () => {
    it('handles 401 unauthorized and clears token', async () => {
      const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent');
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized' }),
      });

      apiClient.setToken('test-token');
      const result = await apiClient.healthCheck();

      expect(result.error).toBeTruthy();
      expect(localStorage.getItem(STORAGE_KEYS.TOKEN)).toBeNull();
      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'auth-expired',
        })
      );
    });

    it('handles network errors', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Network error')
      );

      const result = await apiClient.healthCheck();

      expect(result.error).toBe('Network error');
      expect(result.status).toBe(0);
    });

    it('handles invalid JSON responses', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const result = await apiClient.healthCheck();

      expect(result.data).toEqual({});
    });
  });

  describe('authorization', () => {
    it('includes Authorization header when token is set', async () => {
      apiClient.setToken('test-token');
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await apiClient.healthCheck();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
    });
  });
});

