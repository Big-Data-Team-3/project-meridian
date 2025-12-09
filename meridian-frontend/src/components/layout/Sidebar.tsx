'use client';

import { useState, type ReactElement } from 'react';
import { useConversations } from '@/hooks/useConversations';
import { useConversation } from '@/contexts/ConversationContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
}

export function Sidebar({ isOpen, onClose, onNewChat }: SidebarProps): ReactElement {
  const { conversations, isLoading, deleteConversation, isDeleting } = useConversations();
  const { activeConversationId, setActiveConversationId } = useConversation();

  const handleConversationClick = (id: string): void => {
    setActiveConversationId(id);
    onClose();
  };

  const handleDelete = async (e: React.MouseEvent, id: string): Promise<void> => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this conversation?')) {
      deleteConversation(id);
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
    }
  };

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-[60px] left-0 bottom-0 w-[260px]',
          'bg-surface border-r border-border',
          'transform transition-transform duration-300',
          // Mobile: overlay with z-50
          'z-50 lg:z-40',
          // Mobile: slide in/out
          isOpen ? 'translate-x-0' : '-translate-x-full',
          // Desktop: show when open, hide when closed
          isOpen ? 'lg:translate-x-0' : 'lg:-translate-x-full',
          // Disable pointer events when hidden to prevent interaction
          !isOpen && 'pointer-events-none'
        )}
      >
        <div className="h-full flex flex-col">
          <div className="p-4 border-b border-border">
            <Button
              variant="primary"
              size="md"
              onClick={onNewChat}
              className="w-full"
            >
              + New Chat
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {isLoading ? (
              <div className="text-text-secondary text-sm text-center py-8">
                Loading conversations...
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-text-secondary text-sm text-center py-8">
                No conversations yet
              </div>
            ) : (
              <nav className="space-y-1" aria-label="Conversation history">
                {conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => handleConversationClick(conversation.id)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-lg',
                      'text-sm text-text-primary',
                      'hover:bg-surface-hover transition-colors',
                      'flex items-center justify-between group',
                      activeConversationId === conversation.id &&
                        'bg-surface-hover font-medium'
                    )}
                  >
                    <span className="truncate flex-1">{conversation.title}</span>
                    <button
                      onClick={(e) => handleDelete(e, conversation.id)}
                      className="opacity-0 group-hover:opacity-100 ml-2 p-1 hover:bg-error/20 rounded transition-opacity"
                      aria-label={`Delete conversation ${conversation.title}`}
                      disabled={isDeleting}
                    >
                      <svg
                        className="w-4 h-4 text-error"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </button>
                ))}
              </nav>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}

