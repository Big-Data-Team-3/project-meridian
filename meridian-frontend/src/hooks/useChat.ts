import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { Message, SendMessageRequest, GetMessagesResponse } from '@/types';

export function useChat(conversationId: string | null) {
  const queryClient = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);

  const {
    data: messagesData,
    isLoading: isLoadingMessages,
    error: messagesError,
    refetch: refetchMessages,
  } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: async () => {
      if (!conversationId) return { messages: [], conversationId: '' };
      const response = await apiClient.getMessages(conversationId);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to fetch messages');
      }
      return response.data;
    },
    enabled: !!conversationId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      setIsStreaming(true);
      const request: SendMessageRequest = {
        message,
        conversationId: conversationId || undefined,
      };
      const response = await apiClient.sendMessage(request);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to send message');
      }
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate and refetch messages
      queryClient.invalidateQueries({ queryKey: ['messages', data.conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setIsStreaming(false);
    },
    onError: () => {
      setIsStreaming(false);
    },
  });

  const sendMessage = useCallback(
    (message: string) => {
      sendMessageMutation.mutate(message);
    },
    [sendMessageMutation]
  );

  return {
    messages: messagesData?.messages || [],
    isLoading: isLoadingMessages,
    error: messagesError,
    sendMessage,
    isSending: sendMessageMutation.isPending,
    isStreaming,
    refetchMessages,
  };
}

