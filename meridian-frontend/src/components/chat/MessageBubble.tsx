'use client';

import { type ReactElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// import rehypeHighlight from 'rehype-highlight';
import type { Message } from '@/types';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { useAgent } from '@/contexts/AgentContext';
import { AnalysisBreakdown } from './AnalysisBreakdown';
// import 'highlight.js/styles/github-dark.css';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps): ReactElement {
  const isUser = message.role === 'user';
  const { setTraceFromMessage, openTrace } = useAgent();
  
  const handleViewTrace = () => {
    if (message.agentTrace) {
      setTraceFromMessage(message.agentTrace);
      openTrace();
    }
  };

  const handleCopyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
    } catch (err) {
      console.error('Failed to copy message:', err);
    }
  };

  return (
    <div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'rounded-2xl px-4 py-3',
          'shadow-sm',
          isUser
            ? 'max-w-[85%] bg-accent text-white rounded-br-md'
            : 'w-full max-w-full bg-surface text-text-primary rounded-bl-md border border-border'
        )}
      >
        <div className="prose prose-sm max-w-none dark:prose-invert m-0">
          {isUser ? (
            <p className="text-white m-0 whitespace-pre-wrap">{message.content}</p>
          ) : (
            <>
              {/* Main response content */}
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
              
              {/* Agent Analysis Breakdown */}
              {message.agentAnalysis && (
                <AnalysisBreakdown
                  state={message.agentAnalysis.state}
                  decision={message.agentAnalysis.decision}
                  company={message.agentAnalysis.company}
                  date={message.agentAnalysis.date}
                />
              )}
            </>
          )}
        </div>
        <div
          className={cn(
            'flex items-center justify-between gap-2 mt-2',
            isUser ? 'text-white/70' : 'text-text-secondary'
          )}
        >
          <span className="text-xs">{formatDate(message.timestamp)}</span>
          {!isUser && message.agentTrace && (
            <div className="flex items-center gap-1">
              <button
                onClick={handleCopyMessage}
                className={cn(
                  'text-xs p-1.5 rounded',
                  'bg-surface-hover hover:bg-surface-tertiary',
                  'text-text-secondary hover:text-text-primary',
                  'transition-colors',
                  'flex items-center justify-center'
                )}
                title="Copy message"
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </button>
            <button
              onClick={handleViewTrace}
              className={cn(
                'text-xs px-2 py-1 rounded',
                'bg-surface-hover hover:bg-surface-tertiary',
                'text-text-secondary hover:text-text-primary',
                'transition-colors',
                'flex items-center gap-1'
              )}
              title="View agent trace"
            >
              <svg
                className="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <span>Trace ({message.agentTrace.agentsCalled.length} agents)</span>
            </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

