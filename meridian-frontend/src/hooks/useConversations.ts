import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { Conversation, CreateConversationResponse } from '@/types';

export function useConversations() {
  const queryClient = useQueryClient();

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
      return response.data.conversations;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const createMutation = useMutation({
    mutationFn: async (title?: string): Promise<Conversation> => {
      const response = await apiClient.createConversation(title);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to create conversation');
      }
      return response.data.conversation;
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

