"""
Orchestrator Data Models

Defines data models for orchestrator operations including aggregation
and execution results.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from agents_module.utils.output_schema import AgentOutput


class AgentExecutionResult(BaseModel):
    """Result of a single agent execution."""
    
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Execution status: success, failure, partial, skipped")
    output: Optional[AgentOutput] = Field(None, description="Agent output if successful")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    start_time: Optional[datetime] = Field(None, description="Execution start time")
    end_time: Optional[datetime] = Field(None, description="Execution end time")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    criticality: str = Field(..., description="Agent criticality: critical or non-critical")
    was_aborted: bool = Field(False, description="Whether execution was aborted due to critical failure")


class AggregatedContext(BaseModel):
    """
    Unified context containing all agent outputs and execution metadata.
    
    This is the output of the orchestrator aggregation step and is used
    by the Final Synthesizer to generate the final answer.
    """
    
    agent_outputs: Dict[str, AgentOutput] = Field(
        default_factory=dict,
        description="Agent outputs indexed by agent_id. Only includes successful outputs."
    )
    agent_statuses: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of each agent: success, failure, partial, skipped"
    )
    errors: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Error information for failed agents, indexed by agent_id"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata including timestamps, durations, etc."
    )
    criticality_info: Dict[str, str] = Field(
        default_factory=dict,
        description="Criticality mapping: agent_id -> criticality level"
    )
    execution_plan: Optional[Dict[str, Any]] = Field(
        None,
        description="Original execution plan that generated this context"
    )
    workflow_aborted: bool = Field(
        False,
        description="Whether workflow was aborted due to critical agent failure"
    )
    aborted_at_agent: Optional[str] = Field(
        None,
        description="Agent ID where workflow was aborted (if aborted)"
    )
    partial_results_available: bool = Field(
        False,
        description="Whether partial results are available (workflow aborted but some agents succeeded)"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_outputs": {k: v.model_dump() for k, v in self.agent_outputs.items()},
            "agent_statuses": self.agent_statuses,
            "errors": self.errors,
            "metadata": self.metadata,
            "criticality_info": self.criticality_info,
            "execution_plan": self.execution_plan,
            "workflow_aborted": self.workflow_aborted,
            "aborted_at_agent": self.aborted_at_agent,
            "partial_results_available": self.partial_results_available
        }
    
    def get_successful_agents(self) -> List[str]:
        """Get list of agent IDs that executed successfully."""
        return [agent_id for agent_id, status in self.agent_statuses.items() 
                if status == "success"]
    
    def get_failed_agents(self) -> List[str]:
        """Get list of agent IDs that failed."""
        return [agent_id for agent_id, status in self.agent_statuses.items() 
                if status == "failure"]
    
    def get_critical_failures(self) -> List[str]:
        """Get list of critical agents that failed."""
        return [agent_id for agent_id in self.get_failed_agents()
                if self.criticality_info.get(agent_id) == "critical"]
    
    def has_critical_failure(self) -> bool:
        """Check if any critical agent failed."""
        return len(self.get_critical_failures()) > 0

