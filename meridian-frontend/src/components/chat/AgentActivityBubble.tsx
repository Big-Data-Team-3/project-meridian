'use client';

import { type ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { AgentIcon } from './AgentIcon';
import { useAgent } from '@/contexts/AgentContext';

interface AgentActivityBubbleProps {
  onClick?: () => void;
  expanded?: boolean;
}

export function AgentActivityBubble({ onClick, expanded }: AgentActivityBubbleProps): ReactElement {
  const { currentActivity, trace, isTraceOpen, openTrace } = useAgent();

  if (!currentActivity || currentActivity.status !== 'active') {
    return <></>;
  }

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      openTrace();
    }
  };

  const progress = currentActivity.progress ?? 0;
  const hasTool = !!currentActivity.currentTool;

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg',
        'bg-surface-secondary border border-border',
        'transition-all duration-200',
        expanded && 'w-full',
        onClick && 'cursor-pointer hover:bg-surface-hover',
        !expanded && 'max-w-md'
      )}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <AgentIcon agentName={currentActivity.displayName} size="md" />
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-text-primary truncate">
            {currentActivity.displayName}
          </span>
          {hasTool && (
            <span className="text-xs text-text-secondary">
              • {currentActivity.currentTool}
            </span>
          )}
        </div>
        
        {expanded && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-surface-tertiary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-text-secondary min-w-[3rem] text-right">
                {progress}%
              </span>
            </div>
            
            {trace && trace.agentsCalled.length > 0 && (
              <div className="text-xs text-text-secondary">
                {trace.agentsCalled.length} agent{trace.agentsCalled.length !== 1 ? 's' : ''} active
              </div>
            )}
          </div>
        )}
        
        {!expanded && (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            {hasTool && (
              <span className="text-xs text-text-secondary truncate max-w-[8rem]">
                {currentActivity.currentTool}
              </span>
            )}
          </div>
        )}
      </div>
      
      <div className="text-text-secondary">
        <svg
          className={cn(
            'w-5 h-5 transition-transform duration-200',
            isTraceOpen && 'rotate-180'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
      </div>
    </div>
  );
}

