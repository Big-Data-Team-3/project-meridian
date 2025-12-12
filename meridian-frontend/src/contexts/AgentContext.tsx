'use client';

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { AgentActivity, AgentStreamEvent, AgentTrace } from '@/types/agent';
import type { AgentAnalysis } from '@/types/chat';

interface AgentContextValue {
  // Current agent activity
  currentActivity: AgentActivity | null;
  isAgentActive: boolean;
  
  // Agent trace for sidebar
  trace: AgentTrace | null;
  isTraceOpen: boolean;
  
  // Agent analysis data for PDF download
  agentAnalysis: AgentAnalysis | null;
  
  // Actions
  updateActivity: (event: AgentStreamEvent) => void;
  clearActivity: () => void;
  toggleTrace: () => void;
  openTrace: () => void;
  closeTrace: () => void;
  setTraceFromMessage: (trace: AgentTrace, analysis?: AgentAnalysis) => void;  // Restore trace from persisted message
}

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [currentActivity, setCurrentActivity] = useState<AgentActivity | null>(null);
  const [trace, setTrace] = useState<AgentTrace | null>(null);
  const [isTraceOpen, setIsTraceOpen] = useState(false);
  const [agentAnalysis, setAgentAnalysis] = useState<AgentAnalysis | null>(null);

  const updateActivity = useCallback((event: AgentStreamEvent) => {
    // Update current activity
    if (event.event_type === 'agent_active' && event.agent_name) {
      setCurrentActivity((prev) => {
        const now = new Date();
        return {
          agentName: event.agent_name!,
          displayName: event.agent_name || 'Unknown Agent',
          status: 'active' as const,
          progress: event.progress,
          currentTool: event.event_type === 'tool_usage' ? (event.data?.tool_name as string | undefined) : prev?.currentTool,
          startTime: prev?.startTime || now,
          lastUpdate: now,
        };
      });
    } else if (event.event_type === 'analysis_start' || event.event_type === 'orchestration_start') {
      // Initialize trace
      const startTime = new Date();
      setTrace({
        events: [event],
        agentsCalled: [],
        totalProgress: 0,
        startTime,
      });
      const displayMessage = event.event_type === 'orchestration_start' 
        ? (event.message || 'Starting agent workflow')
        : 'Starting Analysis';
      setCurrentActivity({
        agentName: 'system',
        displayName: displayMessage,
        status: 'active' as const,
        startTime,
        lastUpdate: startTime,
      });
      // Automatically open trace sidebar when analysis starts
      setIsTraceOpen(true);
    } else if (event.event_type === 'tool_usage' && event.agent_name) {
      // Update tool usage
      setCurrentActivity((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          currentTool: typeof event.data?.tool_name === 'string' ? event.data.tool_name : undefined,
          lastUpdate: new Date(),
        };
      });
    } else if (event.event_type === 'progress') {
      // Update progress
      setCurrentActivity((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          progress: event.progress,
          lastUpdate: new Date(),
        };
      });
    } else if (event.event_type === 'analysis_complete' || event.event_type === 'complete' || event.event_type === 'orchestration_complete') {
      // Mark as complete
      setCurrentActivity((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'complete' as const,
          progress: 100,
          lastUpdate: new Date(),
        };
      });
      
      // Extract and store agent analysis data for PDF download
      if (event.data) {
        const data = event.data as any;
        if (data.company && data.date && data.decision && data.state) {
          setAgentAnalysis({
            company: data.company,
            date: data.date,
            decision: data.decision,
            state: data.state || data,
          });
        } else if (data) {
          // Try to extract from the data object itself
          setAgentAnalysis({
            company: data.company || 'UNKNOWN',
            date: data.date || new Date().toISOString().split('T')[0],
            decision: data.decision || 'UNKNOWN',
            state: data,
          });
        }
      }
      
      // Update trace
      setTrace((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          events: [...prev.events, event],
          totalProgress: 100,
          endTime: new Date(),
        };
      });
      
      // Clear activity after a delay
      setTimeout(() => {
        setCurrentActivity(null);
      }, 2000);
    } else if (event.event_type === 'error') {
      setCurrentActivity((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'idle' as const,
          lastUpdate: new Date(),
        };
      });
    }
    
    // Always update trace with new event
    setTrace((prev) => {
      if (!prev) {
        // Initialize trace if it doesn't exist
        return {
          events: [event],
          agentsCalled: event.agent_name ? [event.agent_name] : [],
          totalProgress: event.progress || 0,
          startTime: new Date(),
        };
      }
      
      const agentsCalled = new Set(prev.agentsCalled);
      if (event.agent_name) {
        agentsCalled.add(event.agent_name);
      }
      
      return {
        ...prev,
        events: [...prev.events, event],
        agentsCalled: Array.from(agentsCalled),
        totalProgress: event.progress ?? prev.totalProgress,
      };
    });
  }, []);

  const clearActivity = useCallback(() => {
    setCurrentActivity(null);
    setTrace(null);
    setIsTraceOpen(false);
  }, []);

  const toggleTrace = useCallback(() => {
    setIsTraceOpen((prev) => !prev);
  }, []);

  const openTrace = useCallback(() => {
    setIsTraceOpen(true);
  }, []);

  const closeTrace = useCallback(() => {
    setIsTraceOpen(false);
  }, []);

  const setTraceFromMessage = useCallback((trace: AgentTrace, analysis?: AgentAnalysis) => {
    setTrace(trace);
    setAgentAnalysis(analysis || null);
    setIsTraceOpen(true);
  }, []);

  const value: AgentContextValue = {
    currentActivity,
    isAgentActive: currentActivity?.status === 'active',
    trace,
    isTraceOpen,
    agentAnalysis,
    updateActivity,
    clearActivity,
    toggleTrace,
    openTrace,
    closeTrace,
    setTraceFromMessage,
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgent() {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgent must be used within an AgentProvider');
  }
  return context;
}

