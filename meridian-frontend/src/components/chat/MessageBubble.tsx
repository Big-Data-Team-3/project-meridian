'use client';

import { type ReactElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// import rehypeHighlight from 'rehype-highlight';
import type { Message } from '@/types';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';
// import 'highlight.js/styles/github-dark.css';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps): ReactElement {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3',
          'shadow-sm',
          isUser
            ? 'bg-accent text-white rounded-br-md'
            : 'bg-surface text-text-primary rounded-bl-md border border-border'
        )}
      >
        <div className="prose prose-sm max-w-none dark:prose-invert m-0">
          {isUser ? (
            <p className="text-white m-0 whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ node, className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || '');
                  return match ? (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className="bg-surface-hover px-1 py-0.5 rounded text-sm" {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>
        <div
          className={cn(
            'text-xs mt-2',
            isUser ? 'text-white/70' : 'text-text-secondary'
          )}
        >
          {formatDate(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

