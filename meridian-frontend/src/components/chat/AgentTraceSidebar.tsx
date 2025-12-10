'use client';

import { useEffect, type ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { useAgent } from '@/contexts/AgentContext';
import { AgentTraceTimeline } from './AgentTraceTimeline';

interface AgentTraceSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AgentTraceSidebar({ isOpen, onClose }: AgentTraceSidebarProps): ReactElement {
  const { trace, currentActivity } = useAgent();

  // Close sidebar when Escape key is pressed
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when sidebar is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return <></>;
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-50 lg:z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 right-0 bottom-0 w-full sm:w-[480px] lg:w-[520px]',
          'bg-surface border-l border-border',
          'transform transition-transform duration-300 ease-in-out',
          'z-50 lg:z-40',
          'flex flex-col',
          'shadow-xl'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface-secondary">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-text-primary">Agent Trace</h2>
            {currentActivity && (
              <div className="flex items-center gap-2 px-2 py-1 bg-surface-tertiary rounded-md">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs text-text-secondary">Active</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
            aria-label="Close trace sidebar"
          >
            <svg
              className="w-5 h-5 text-text-secondary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {trace ? (
            <AgentTraceTimeline trace={trace} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-text-secondary mb-2">No agent trace available</p>
              <p className="text-sm text-text-secondary opacity-75">
                Agent activity will appear here when agents are active
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        {trace && trace.agentsCalled.length > 0 && (
          <div className="p-4 border-t border-border bg-surface-secondary">
            <div className="text-xs text-text-secondary mb-2">
              {trace.agentsCalled.length} agent{trace.agentsCalled.length !== 1 ? 's' : ''} involved in this analysis
            </div>
            <div className="flex flex-wrap gap-2">
              {trace.agentsCalled.map((agentName) => (
                <div
                  key={agentName}
                  className="flex items-center gap-1.5 px-2 py-1 bg-surface-tertiary rounded-md"
                >
                  <span className="text-xs text-text-primary">{agentName}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

