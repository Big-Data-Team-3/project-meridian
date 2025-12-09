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
        "fixed bottom-0 right-0 bg-bg-primary/80 backdrop-blur-sm border-t border-border transition-all duration-300 z-30",
        sidebarOpen ? "lg:left-[260px]" : "lg:left-0",
        "left-0" // Mobile: full width
      )}
    >
      <div className="max-w-3xl mx-auto px-4 py-4">
        <div className="relative flex items-end gap-2 bg-surface border border-border rounded-2xl px-4 py-2.5 shadow-sm hover:shadow-md focus-within:border-accent/60 focus-within:shadow-lg focus-within:shadow-accent/5 transition-all duration-200">
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
              'placeholder:text-text-secondary/60',
              'focus:outline-none',
              'max-h-[200px] overflow-y-auto',
              'text-base leading-6',
              'py-1.5'
            )}
            aria-label="Message input"
          />
          <button
            onClick={handleSend}
            disabled={!message.trim() || disabled}
            className={cn(
              'flex items-center justify-center flex-shrink-0',
              'w-8 h-8 rounded-lg transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              message.trim() && !disabled
                ? 'bg-accent text-white hover:bg-accent-hover hover:scale-105 active:scale-95 shadow-sm'
                : 'bg-transparent text-text-secondary/50 cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            {message.trim() && !disabled ? (
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            ) : (
              <svg
                className="w-4 h-4"
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
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

