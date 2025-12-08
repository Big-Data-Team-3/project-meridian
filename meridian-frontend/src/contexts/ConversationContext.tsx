'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { Conversation } from '@/types';

interface ConversationContextType {
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

export function ConversationProvider({ children }: { children: React.ReactNode }) {
  const [activeConversationId, setActiveConversationIdState] = useState<string | null>(null);

  const setActiveConversationId = useCallback((id: string | null): void => {
    setActiveConversationIdState(id);
  }, []);

  return (
    <ConversationContext.Provider
      value={{
        activeConversationId,
        setActiveConversationId,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversation(): ConversationContextType {
  const context = useContext(ConversationContext);
  if (context === undefined) {
    throw new Error('useConversation must be used within a ConversationProvider');
  }
  return context;
}

