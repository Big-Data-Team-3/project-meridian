import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { Message, SendMessageRequest, GetMessagesResponse } from '@/types';

export function useChat(conversationId: string | null) {
  const queryClient = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<Message[]>([]);

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
      // Map backend messages to frontend messages
      const backendMessages = response.data.messages || [];
      const messages = backendMessages.map((msg) => ({
        id: msg.message_id,
        role: msg.role as Message['role'],
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        conversationId: msg.thread_id,
      }));
      return { messages, conversationId: response.data.thread_id };
    },
    enabled: !!conversationId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!conversationId) {
        throw new Error('No conversation selected');
      }
      
      // Add optimistic user message
      const optimisticUserMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
        conversationId: conversationId,
      };
      setOptimisticMessages((prev) => [...prev, optimisticUserMessage]);
      
      setIsStreaming(true);
      const request: SendMessageRequest = {
        message,
        conversationId: conversationId,
      };
      const response = await apiClient.sendMessage(request);
      if (response.error || !response.data) {
        // Remove optimistic message on error
        setOptimisticMessages((prev) => prev.filter((m) => m.id !== optimisticUserMessage.id));
        throw new Error(response.error || 'Failed to send message');
      }
      
      // Add optimistic assistant message
      const optimisticAssistantMessage: Message = {
        id: response.data.assistant_message_id,
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
        conversationId: response.data.thread_id,
      };
      setOptimisticMessages((prev) => [...prev, optimisticAssistantMessage]);
      
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate and refetch messages to get updated conversation
      queryClient.invalidateQueries({ queryKey: ['messages', data.thread_id] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setIsStreaming(false);
      // Clear optimistic messages after refetch
      setTimeout(() => setOptimisticMessages([]), 1000);
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
      setIsStreaming(false);
      // Clear optimistic messages on error
      setOptimisticMessages([]);
    },
  });

  const sendMessage = useCallback(
    (message: string) => {
      sendMessageMutation.mutate(message);
    },
    [sendMessageMutation]
  );

  // Combine fetched messages with optimistic messages, sorted chronologically
  const allMessages = [...(messagesData?.messages || []), ...optimisticMessages];
  const sortedMessages = allMessages.sort((a, b) => 
    a.timestamp.getTime() - b.timestamp.getTime()
  );
  
  // Remove duplicates (in case optimistic messages overlap with fetched)
  const uniqueMessages = sortedMessages.reduce((acc, msg) => {
    if (!acc.find((m) => m.id === msg.id)) {
      acc.push(msg);
    }
    return acc;
  }, [] as Message[]);

  return {
    messages: uniqueMessages,
    isLoading: isLoadingMessages,
    error: messagesError,
    sendMessage,
    isSending: sendMessageMutation.isPending,
    isStreaming,
    refetchMessages,
  };
}

