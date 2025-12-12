import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import type { Conversation, CreateConversationResponse } from '@/types';

export function useConversations() {
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      const response = await apiClient.getConversations();
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to fetch conversations');
      }
      // Map backend threads to frontend conversations
      const conversations = (response.data.threads || []).map((thread) => ({
        id: thread.thread_id,
        title: thread.title || 'New Conversation',
        createdAt: new Date(thread.created_at),
        updatedAt: new Date(thread.updated_at),
        messageCount: typeof thread.message_count === 'number' ? thread.message_count : 0,
      }));

      // Sort by most recently updated first
      return conversations.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
    },
    enabled: isAuthenticated && !authLoading, // Only fetch when authenticated
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const createMutation = useMutation({
    mutationFn: async (title?: string): Promise<Conversation> => {
      const response = await apiClient.createConversation(title);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to create conversation');
      }
      // Map backend thread to frontend conversation
      const thread = response.data;
      return {
        id: thread.thread_id,
        title: thread.title || 'New Conversation',
        createdAt: new Date(thread.created_at),
        updatedAt: new Date(thread.updated_at),
        messageCount: 0,
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (conversationId: string) => {
      const response = await apiClient.deleteConversation(conversationId);
      if (response.error) {
        throw new Error(response.error || 'Failed to delete conversation');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  return {
    conversations: data || [],
    isLoading,
    error,
    refetch,
    createConversation: createMutation.mutateAsync,
    deleteConversation: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}

