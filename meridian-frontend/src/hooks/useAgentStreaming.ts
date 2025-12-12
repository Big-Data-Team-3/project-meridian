'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useAgent } from '@/contexts/AgentContext';
import { STORAGE_KEYS } from '@/lib/storage';
import type { AgentStreamEvent } from '@/types/agent';

interface UseAgentStreamingOptions {
  enabled?: boolean;
  onError?: (error: Error) => void;
  onComplete?: () => void;  // Callback when streaming completes successfully
}

/**
 * Hook to connect to SSE stream for agent activity updates
 */
export function useAgentStreaming(
  conversationContext: Array<{ role: string; content: string; timestamp?: string }> = [],
  options: UseAgentStreamingOptions = {},
  threadId?: string
) {
  const { updateActivity, clearActivity } = useAgent();
  const { enabled = true, onError, onComplete } = options;
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startStreaming = useCallback(
    async (message: string) => {
      if (!enabled) return;

      // Clear previous activity
      clearActivity();

      // Abort any existing stream
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      abortControllerRef.current = new AbortController();

      try {
        // Get auth token from storage
        let token: string | null = null;
        
        try {
          const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
          if (storedToken) {
            // Token is stored as JSON string
            token = JSON.parse(storedToken);
          }
        } catch {
          // Try direct access if JSON parsing fails
          token = localStorage.getItem(STORAGE_KEYS.TOKEN);
        }
        
        if (!token) {
          throw new Error('No authentication token found');
        }

        // Company name/ticker extraction is now handled automatically by the backend
        // using LLM-based entity extraction. No need for hardcoded mappings.
        // The backend will extract tickers from the query using the LLM classifier.
        
        // Get today's date in YYYY-MM-DD format
        const today = new Date();
        const tradeDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

        // Prepare request body matching backend expectations
        // Note: company_name is optional - backend will extract it from query using LLM
        const requestBody: {
          query: string;
          company_name?: string;
          trade_date: string;
          conversation_context?: Array<{ role: string; content: string; timestamp?: string }>;
          thread_id?: string;
        } = {
          query: message,
          trade_date: tradeDate,
          conversation_context: conversationContext.map((msg) => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString(),
          })),
        };
        
        // company_name is now optional - backend will extract it automatically
        // Only include if explicitly provided (for backward compatibility)
        
        // Add thread_id if provided (for saving agent response to database)
        if (threadId) {
          requestBody.thread_id = threadId;
        }

        // Use fetch with ReadableStream for SSE
        const response = await fetch('http://localhost:8000/api/streaming/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(requestBody),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        // Read the stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const jsonStr = line.slice(6); // Remove 'data: ' prefix
                if (jsonStr.trim()) {
                  const event: AgentStreamEvent = JSON.parse(jsonStr);
                  updateActivity(event);
                  
                  // Handle error events - call onError callback and stop streaming
                  if (event.event_type === 'error') {
                    console.error('❌ Agent error event received:', event.message);
                    const errorMessage = event.message || 'An error occurred during agent processing';
                    if (onError) {
                      onError(new Error(errorMessage));
                    }
                    // Stop streaming on error
                    if (abortControllerRef.current) {
                      abortControllerRef.current.abort();
                      abortControllerRef.current = null;
                    }
                    // Don't return here - let the stream continue to receive the complete event
                    // The complete event will be handled below
                  }
                  
                  // Check if streaming completed
                  if (event.event_type === 'complete' || event.event_type === 'analysis_complete' || event.event_type === 'orchestration_complete') {
                    // Check if this is an error completion
                    const isErrorCompletion = (event.data as any)?.error === true || (event.data as any)?.stopped === true;
                    
                    if (isErrorCompletion) {
                      console.log('⚠️ Streaming stopped due to error');
                      // onError was already called above if error event was received
                      // But if we only got a complete event with error flag, call onError here
                      if (event.message && onError) {
                        onError(new Error(event.message));
                      }
                    } else {
                      console.log('✅ Streaming complete, calling onComplete callback');
                      if (onComplete) {
                        onComplete();
                      }
                    }
                  }
                }
              } catch (err) {
                console.error('Failed to parse SSE event:', err);
              }
            } else if (line.startsWith(':')) {
              // Comment line (keepalive), ignore
              continue;
            }
          }
        }
        
        // Also call onComplete when stream ends naturally
        if (onComplete) {
          console.log('✅ Stream ended, calling onComplete callback');
          onComplete();
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          // Stream was aborted, this is expected
          return;
        }
        console.error('SSE streaming error:', error);
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
      }
    },
    [conversationContext, enabled, updateActivity, clearActivity, onError, onComplete]
  );

  const stopStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    clearActivity();
  }, [clearActivity]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, [stopStreaming]);

  return {
    startStreaming,
    stopStreaming,
    isStreaming: !!abortControllerRef.current && !abortControllerRef.current.signal.aborted,
  };
}

