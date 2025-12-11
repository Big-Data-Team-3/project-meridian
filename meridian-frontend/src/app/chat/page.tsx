'use client';

import { useState, useEffect, type ReactElement } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useConversation } from '@/contexts/ConversationContext';
import { useChat } from '@/hooks/useChat';
import { useConversations } from '@/hooks/useConversations';
import { useAgentStreaming } from '@/hooks/useAgentStreaming';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { MessageList } from '@/components/chat/MessageList';
import { InputBar } from '@/components/chat/InputBar';
import { AgentTraceSidebar } from '@/components/chat/AgentTraceSidebar';
import { useAgent } from '@/contexts/AgentContext';
import { cn } from '@/lib/utils';

export default function ChatPage(): ReactElement | null {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, authError, clearAuthError, logout } = useAuth();
  const { activeConversationId, setActiveConversationId } = useConversation();
  const { messages, sendMessage, isSending, isStreaming, isLoading, error: chatError } = useChat(
    activeConversationId
  );
  const { createConversation, isCreating, error: conversationsError } = useConversations();
  const [sidebarOpen, setSidebarOpen] = useState(true); // Default to open on desktop
  
  // Prepare conversation context for agent streaming
  const conversationContext = messages.map((msg) => ({
    role: msg.role,
    content: msg.content,
    timestamp: msg.timestamp.toISOString(),
  }));
  
  const { startStreaming } = useAgentStreaming(
    conversationContext,
    {
      enabled: true,
      onError: (error) => {
        console.error('Agent streaming error:', error);
      },
    },
    activeConversationId || undefined
  );
  
  const { isTraceOpen, closeTrace } = useAgent();

  useEffect(() => {
    // Only redirect if auth loading is complete and user is not authenticated
    // This prevents redirecting before auth state is restored from localStorage
    if (!authLoading && !isAuthenticated && !authError) {
      console.log('🔄 Chat page: User not authenticated, redirecting to home');
      router.push('/');
    }
  }, [isAuthenticated, authLoading, authError, router]);

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
    try {
    let conversationId = activeConversationId;
    
    if (!conversationId) {
      // Create a new conversation if none exists
      conversationId = await handleNewChat();
      if (!conversationId) {
        console.error('Failed to create conversation');
          alert('Failed to create conversation. Please try again.');
        return;
      }
    }
    
    // Send message to chat endpoint - backend will classify and route
    const chatResponse = await sendMessage(message);
    
    // Check if backend indicates we should use streaming (agentic query)
    if (chatResponse?.use_streaming) {
      // Backend has classified this as an agentic query - use streaming
      console.log(`Routing to agent service: intent=${chatResponse.intent}, workflow=${chatResponse.workflow}`);
      startStreaming(message);
    } else {
      // Simple chat query - response already received from OpenAI
      console.log(`Using OpenAI response: intent=${chatResponse?.intent || 'simple_chat'}`);
      // The response is already handled by sendMessage mutation
    }
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message. Please try again.');
    }
  };

  const handleReLogin = async (): Promise<void> => {
    await logout();
    clearAuthError();
    router.push('/');
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated && !authError) {
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
          {/* Auth expired banner */}
          {authError && (
            <div className="mx-4 mt-4 p-4 bg-warning/10 border border-warning/30 rounded-lg flex items-center justify-between gap-3">
              <p className="text-warning text-sm">
                {authError}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={clearAuthError}
                  className="text-xs text-text-secondary underline hover:no-underline"
                >
                  Dismiss
                </button>
                <button
                  onClick={handleReLogin}
                  className="text-xs bg-warning text-bg-primary px-3 py-1 rounded-md hover:bg-warning/90"
                >
                  Log in again
                </button>
              </div>
            </div>
          )}

          {/* Error Display */}
          {(chatError || conversationsError) && (
            <div className="mx-4 mt-4 p-4 bg-error/10 border border-error/20 rounded-lg">
              <p className="text-error text-sm">
                {chatError?.message || conversationsError?.message || 'An error occurred'}
              </p>
            </div>
          )}

          {messages.length === 0 && !isLoading ? (
            <div className="flex-1 flex items-center justify-center px-4">
              <div className="text-center max-w-xl space-y-3">
                <h2 className="text-2xl font-semibold text-text-primary">
                  Welcome to Meridian
                </h2>
                <p className="text-text-secondary">
                  Ask about financial data, stocks, market moves, or get quick summaries.
                  Start typing below to begin a new conversation.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  <span className="text-xs px-3 py-2 rounded-full bg-surface-hover text-text-secondary">
                    “What moved markets today?”
                  </span>
                  <span className="text-xs px-3 py-2 rounded-full bg-surface-hover text-text-secondary">
                    “Compare SPY vs QQQ over 6 months”
                  </span>
                  <span className="text-xs px-3 py-2 rounded-full bg-surface-hover text-text-secondary">
                    “Summarize news for AAPL”
                  </span>
                </div>
              </div>
            </div>
          ) : isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-text-secondary">Loading messages...</div>
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
      
      {/* Agent Trace Sidebar */}
      <AgentTraceSidebar isOpen={isTraceOpen} onClose={closeTrace} />
    </div>
  );
}

