'use client';

import { useEffect, useRef, type ReactElement } from 'react';
import type { Message } from '@/types';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { AgentActivityBubble } from './AgentActivityBubble';
import { useAgent } from '@/contexts/AgentContext';

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps): ReactElement {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isAgentActive, openTrace } = useAgent();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming, isAgentActive]);

  // Show AgentActivityBubble when agents are active, otherwise show TypingIndicator
  const showAgentBubble = isAgentActive;
  const showTypingIndicator = isStreaming && !isAgentActive;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 pb-24">
      <div className="space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {showAgentBubble && (
          <AgentActivityBubble onClick={openTrace} expanded={false} />
        )}
        {showTypingIndicator && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

