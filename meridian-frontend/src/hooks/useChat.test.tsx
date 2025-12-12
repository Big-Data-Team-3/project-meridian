import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useChat } from './useChat';
import { apiClient } from '@/lib/api';
import * as useAuthModule from '@/hooks/useAuth';

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getMessages: vi.fn(),
    sendMessage: vi.fn(),
  },
}));

// Mock useAuth
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: null,
      authError: null,
      clearAuthError: vi.fn(),
      loginWithGoogle: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });
  });

  it('returns empty messages when conversationId is null', () => {
    const { result } = renderHook(() => useChat(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it('fetches messages for a conversation', async () => {
    const mockMessages = {
      thread_id: 'thread-1',
      messages: [
        {
          message_id: 'msg-1',
          role: 'user',
          content: 'Hello',
          timestamp: '2024-01-01T10:00:00Z',
          thread_id: 'thread-1',
          metadata: {},
        },
        {
          message_id: 'msg-2',
          role: 'assistant',
          content: 'Hi there!',
          timestamp: '2024-01-01T10:01:00Z',
          thread_id: 'thread-1',
          metadata: {},
        },
      ],
    };

    vi.mocked(apiClient.getMessages).mockResolvedValueOnce({
      data: mockMessages,
      status: 200,
    });

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].content).toBe('Hello');
    expect(result.current.messages[1].content).toBe('Hi there!');
  });

  it('sends a message and adds optimistic update', async () => {
    const mockSendResponse = {
      thread_id: 'thread-1',
      message_id: 'msg-1',
      response: 'Assistant response',
      use_streaming: false,
      assistant_message_id: 'msg-2',
    };

    vi.mocked(apiClient.sendMessage).mockResolvedValueOnce({
      data: mockSendResponse,
      status: 200,
    });

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    await result.current.sendMessage('User message');

    expect(apiClient.sendMessage).toHaveBeenCalledWith({
      conversationId: 'thread-1',
      message: 'User message',
    });
  });

  it('handles send message error', async () => {
    vi.mocked(apiClient.sendMessage).mockResolvedValueOnce({
      data: {} as any,
      error: 'Failed to send',
      status: 500,
    });

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    await expect(result.current.sendMessage('Test')).rejects.toThrow();
  });

  it('does not fetch when not authenticated', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      authError: null,
      clearAuthError: vi.fn(),
      loginWithGoogle: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    expect(apiClient.getMessages).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });

  it('handles messages with agent trace', async () => {
    const mockMessages = {
      thread_id: 'thread-1',
      messages: [
        {
          message_id: 'msg-1',
          role: 'assistant',
          content: 'Analysis complete',
          timestamp: '2024-01-01T10:00:00Z',
          thread_id: 'thread-1',
          metadata: {
            agent_trace: {
              events: [],
              agents_called: ['analyst', 'trader'],
            },
            agent_analysis: {
              company: 'AAPL',
              date: '2024-01-01',
              decision: 'BUY',
              state: {},
            },
          },
        },
      ],
    };

    vi.mocked(apiClient.getMessages).mockResolvedValueOnce({
      data: mockMessages,
      status: 200,
    });

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.messages[0].agentTrace).toBeDefined();
    expect(result.current.messages[0].agentTrace?.agentsCalled).toEqual([
      'analyst',
      'trader',
    ]);
    expect(result.current.messages[0].agentAnalysis?.company).toBe('AAPL');
  });

  it('sets isSending state during message send', async () => {
    let resolveSend: (value: any) => void;
    const sendPromise = new Promise((resolve) => {
      resolveSend = resolve;
    });

    vi.mocked(apiClient.sendMessage).mockReturnValueOnce(sendPromise as any);

    const { result } = renderHook(() => useChat('thread-1'), {
      wrapper: createWrapper(),
    });

    const sendPromise2 = result.current.sendMessage('Test');

    await waitFor(() => {
      expect(result.current.isSending).toBe(true);
    });

    resolveSend!({
      data: {
        thread_id: 'thread-1',
        message_id: 'msg-1',
        response: 'Response',
        use_streaming: false,
        assistant_message_id: null,
      },
      status: 200,
    });

    await sendPromise2;
    await waitFor(() => {
      expect(result.current.isSending).toBe(false);
    });
  });
});

