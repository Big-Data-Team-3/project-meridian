'use client';

import { useState, useRef, useEffect, type KeyboardEvent, type ReactElement } from 'react';
import { cn } from '@/lib/utils';

interface InputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  sidebarOpen?: boolean;
}

export function InputBar({
  onSend,
  disabled = false,
  placeholder = 'Ask about financial data, stocks, or market analysis...',
  sidebarOpen = false,
}: InputBarProps): ReactElement {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSend = (): void => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div 
      className={cn(
        "fixed bottom-0 right-0 bg-bg-primary border-t border-border p-4 transition-all duration-300 z-30",
        sidebarOpen ? "lg:left-[260px]" : "lg:left-0",
        "left-0" // Mobile: full width
      )}
    >
      <div className="max-w-[768px] mx-auto">
        <div className="relative flex items-end gap-2 bg-surface border border-border rounded-2xl px-4 py-3 focus-within:ring-2 focus-within:ring-accent focus-within:border-transparent transition-all">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              'flex-1 resize-none bg-transparent text-text-primary',
              'placeholder:text-text-secondary',
              'focus:outline-none',
              'max-h-[200px] overflow-y-auto',
              'text-base leading-6'
            )}
            aria-label="Message input"
          />
          <button
            onClick={handleSend}
            disabled={!message.trim() || disabled}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-accent',
              message.trim() && !disabled
                ? 'bg-accent text-white hover:bg-accent-hover'
                : 'bg-surface-hover text-text-secondary cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

