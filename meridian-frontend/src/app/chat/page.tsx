'use client';

import { useState, useEffect, type ReactElement } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useConversation } from '@/contexts/ConversationContext';
import { useChat } from '@/hooks/useChat';
import { useConversations } from '@/hooks/useConversations';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { MessageList } from '@/components/chat/MessageList';
import { InputBar } from '@/components/chat/InputBar';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export default function ChatPage(): ReactElement | null {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { activeConversationId, setActiveConversationId } = useConversation();
  const { messages, sendMessage, isSending, isStreaming, isLoading } = useChat(
    activeConversationId
  );
  const { createConversation, isCreating } = useConversations();
  const [sidebarOpen, setSidebarOpen] = useState(true); // Default to open on desktop

  useEffect(() => {
    // Only redirect if auth loading is complete and user is not authenticated
    // This prevents redirecting before auth state is restored from localStorage
    if (!authLoading && !isAuthenticated) {
      console.log('🔄 Chat page: User not authenticated, redirecting to home');
      router.push('/');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleNewChat = async (): Promise<string | null> => {
    try {
      const conversation = await createConversation(undefined);
      if (conversation) {
        setActiveConversationId(conversation.id);
        return conversation.id;
      }
      return null;
    } catch (error) {
      console.error('Failed to create conversation:', error);
      return null;
    }
  };

  const handleSendMessage = async (message: string): Promise<void> => {
    let conversationId = activeConversationId;
    
    if (!conversationId) {
      // Create a new conversation if none exists
      conversationId = await handleNewChat();
      if (!conversationId) {
        console.error('Failed to create conversation');
        return;
      }
    }
    
    sendMessage(message);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="h-screen flex flex-col bg-bg-primary overflow-hidden">
      <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} sidebarOpen={sidebarOpen} />
      
      <div className="flex flex-1 pt-[60px] overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewChat={handleNewChat}
        />
        
        <main 
          className={cn(
            "flex-1 flex flex-col overflow-hidden transition-all duration-300",
            // Account for fixed sidebar on desktop when open
            sidebarOpen ? "lg:ml-[260px]" : "lg:ml-0"
          )}
          style={sidebarOpen ? { width: 'calc(100% - 260px)' } : { width: '100%' }}
        >
          {messages.length === 0 && !isLoading ? (
            <div className="flex-1 flex items-center justify-center px-4">
              <div className="text-center max-w-md">
                <h2 className="text-2xl font-semibold text-text-primary mb-2">
                  Welcome to Meridian
                </h2>
                <p className="text-text-secondary mb-6">
                  Ask questions about financial data, stocks, market analysis, or
                  get insights from our multi-agent intelligence system.
                </p>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleNewChat}
                  disabled={isCreating}
                >
                  {isCreating ? 'Creating...' : 'Start New Conversation'}
                </Button>
              </div>
            </div>
          ) : (
            <MessageList messages={messages} isStreaming={isStreaming || isSending} />
          )}
          
          <InputBar
            onSend={handleSendMessage}
            disabled={isSending || isCreating}
            sidebarOpen={sidebarOpen}
          />
        </main>
      </div>

      {/* Mobile sidebar toggle button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed bottom-20 left-4 p-3 bg-accent text-white rounded-full shadow-lg hover:bg-accent-hover transition-colors z-40"
        aria-label="Toggle sidebar"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>
    </div>
  );
}

