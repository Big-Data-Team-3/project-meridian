/**
 * Agent-related types for real-time agent activity tracking
 */

export type AgentEventType =
  | 'analysis_start'
  | 'agent_active'
  | 'tool_usage'
  | 'progress'
  | 'analysis_complete'
  | 'complete'
  | 'error'
  | 'orchestration_start'
  | 'orchestration_complete';

export interface AgentStreamEvent {
  event_type: AgentEventType;
  message: string;
  agent_name?: string;
  progress?: number;
  data?: Record<string, unknown>;
  timestamp: string;
}

export interface AgentActivity {
  agentName: string;
  displayName: string;
  status: 'active' | 'idle' | 'complete';
  progress?: number;
  currentTool?: string;
  startTime: Date;
  lastUpdate: Date;
}

export interface AgentTrace {
  events: AgentStreamEvent[];
  agentsCalled: string[];
  totalProgress: number;
  startTime: Date;
  endTime?: Date;
}

