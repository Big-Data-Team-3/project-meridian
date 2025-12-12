'use client';

import { type ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { AgentIcon } from './AgentIcon';
import type { AgentStreamEvent, AgentTrace } from '@/types/agent';

interface AgentTraceTimelineProps {
  trace: AgentTrace;
}

export function AgentTraceTimeline({ trace }: AgentTraceTimelineProps): ReactElement {
  const getEventIcon = (eventType: AgentStreamEvent['event_type']) => {
    switch (eventType) {
      case 'analysis_start':
        return '🚀';
      case 'agent_active':
        return '👤';
      case 'tool_usage':
        return '🔧';
      case 'progress':
        return '📊';
      case 'analysis_complete':
      case 'complete':
        return '✅';
      case 'error':
        return '❌';
      case 'orchestration_start':
        return '🎯';
      case 'orchestration_complete':
        return '🎉';
      default:
        return '📝';
    }
  };

  const getEventColor = (eventType: AgentStreamEvent['event_type']) => {
    switch (eventType) {
      case 'analysis_start':
      case 'orchestration_start':
        return 'bg-blue-500';
      case 'agent_active':
        return 'bg-green-500';
      case 'tool_usage':
        return 'bg-purple-500';
      case 'progress':
        return 'bg-yellow-500';
      case 'analysis_complete':
      case 'complete':
      case 'orchestration_complete':
        return 'bg-green-600';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      // Validate timestamp exists and is not empty
      if (!timestamp || typeof timestamp !== 'string') {
        return 'just now';
      }

      const date = new Date(timestamp);
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return 'just now';
      }

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      
      // Handle negative differences (future dates) or very small differences
      if (diffSec < 0 || Math.abs(diffSec) < 1) {
        return 'just now';
      }
      
      // Handle small differences (less than a minute)
      if (diffSec < 60) {
        return `${diffSec}s ago`;
      }
      
      // Handle minutes
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) {
        return `${diffMin}m ago`;
      }
      
      // Handle hours
      const diffHour = Math.floor(diffMin / 60);
      if (diffHour < 24) {
        return `${diffHour}h ago`;
      }
      
      // For older dates, show formatted time
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch (error) {
      // Fallback for any parsing errors
      console.warn('Timestamp formatting error:', error, 'timestamp:', timestamp);
      return 'just now';
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary Section */}
      <div className="bg-surface-secondary rounded-lg p-4 border border-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">Analysis Summary</h3>
          {trace.endTime && (
            <span className="text-xs text-text-secondary">
              Completed {formatTimestamp(trace.endTime.toISOString())}
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-text-secondary mb-1">Agents Called</div>
            <div className="text-lg font-semibold text-text-primary">
              {trace.agentsCalled.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-text-secondary mb-1">Progress</div>
            <div className="text-lg font-semibold text-text-primary">
              {trace.totalProgress}%
            </div>
          </div>
        </div>
        
        {trace.agentsCalled.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="text-xs text-text-secondary mb-2">Active Agents:</div>
            <div className="flex flex-wrap gap-2">
              {trace.agentsCalled.map((agentName) => (
                <div
                  key={agentName}
                  className="flex items-center gap-1.5 px-2 py-1 bg-surface-tertiary rounded-md"
                >
                  <AgentIcon agentName={agentName} size="sm" />
                  <span className="text-xs text-text-primary">{agentName}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="space-y-0">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Event Timeline</h3>
        
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />
          
          <div className="space-y-4">
            {trace.events.map((event, index) => {
              const isLast = index === trace.events.length - 1;
              const eventColor = getEventColor(event.event_type);
              
              return (
                <div key={index} className="relative flex items-start gap-4">
                  {/* Timeline dot */}
                  <div className="relative z-10 flex-shrink-0">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-full flex items-center justify-center text-white text-xs',
                        eventColor
                      )}
                    >
                      {getEventIcon(event.event_type)}
                    </div>
                  </div>
                  
                  {/* Event content */}
                  <div className="flex-1 min-w-0 pb-4">
                    <div className="bg-surface-secondary rounded-lg p-3 border border-border">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div className="flex-1 min-w-0">
                          {event.agent_name && (
                            <div className="flex items-center gap-2 mb-1">
                              <AgentIcon agentName={event.agent_name} size="sm" />
                              <span className="text-xs font-medium text-text-primary">
                                {event.agent_name}
                              </span>
                            </div>
                          )}
                          <p className="text-sm text-text-primary">{event.message}</p>
                        </div>
                        <span className="text-xs text-text-secondary whitespace-nowrap">
                          {formatTimestamp(event.timestamp)}
                        </span>
                      </div>
                      
                      {/* Tool usage details */}
                      {event.event_type === 'tool_usage' && event.data && typeof event.data.tool_name === 'string' && (
                        <div className="mt-2 pt-2 border-t border-border">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-text-secondary">Tool:</span>
                            <code className="text-xs bg-surface-tertiary px-2 py-0.5 rounded text-text-primary">
                              {event.data.tool_name}
                            </code>
                            {event.data.tool_args && typeof event.data.tool_args === 'object' ? (
                              <span className="text-xs text-text-secondary">
                                ({Object.keys(event.data.tool_args as Record<string, unknown>).length} params)
                              </span>
                            ) : null}
                          </div>
                        </div>
                      )}
                      
                      {/* Progress indicator */}
                      {event.progress !== undefined && (
                        <div className="mt-2 pt-2 border-t border-border">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary transition-all duration-300"
                                style={{ width: `${event.progress}%` }}
                              />
                            </div>
                            <span className="text-xs text-text-secondary min-w-[3rem] text-right">
                              {event.progress}%
                            </span>
                          </div>
                        </div>
                      )}
                      
                      {/* Additional data */}
                      {event.data && typeof event.data === 'object' && Object.keys(event.data).length > 0 && 
                       event.event_type !== 'tool_usage' && (
                        <details className="mt-2 pt-2 border-t border-border">
                          <summary className="text-xs text-text-secondary cursor-pointer hover:text-text-primary">
                            View details
                          </summary>
                          <pre className="mt-2 text-xs bg-surface-tertiary p-2 rounded overflow-auto max-h-32">
                            {JSON.stringify(event.data, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

