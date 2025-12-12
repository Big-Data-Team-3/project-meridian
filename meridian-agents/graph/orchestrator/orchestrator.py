"""
Orchestrator

Orchestrates agent execution, handles critical vs non-critical failures,
and aggregates results into unified context.
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from agents_module.utils.agent_states import AgentState
from agents_module.utils.output_schema import AgentOutput, validate_agent_output
from ..planner.models import ExecutionPlan
from .models import AggregatedContext, AgentExecutionResult
from .executor import AgentExecutor
from .failure_handler import FailureHandler


class Orchestrator:
    """
    Orchestrates agent execution with criticality-based failure handling.
    
    Responsibilities:
    - Execute agents in sequence according to execution plan
    - Detect critical vs non-critical agent failures
    - Abort workflow on critical failures
    - Continue workflow on non-critical failures
    - Aggregate all agent outputs into unified context
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.executor = AgentExecutor()
    
    def aggregate_results(
        self,
        final_state: Dict[str, Any],
        execution_plan: ExecutionPlan,
        workflow_start_time: datetime,
        execution_trace: Optional[List[Any]] = None
    ) -> AggregatedContext:
        """
        Aggregate agent execution results into unified context.
        
        This method processes the final state after graph execution and:
        - Checks for agent failures
        - Determines if workflow should be aborted (critical failure)
        - Aggregates all successful outputs
        - Creates unified context for synthesizer
        
        Args:
            final_state: Final state from graph execution
            execution_plan: Execution plan with agent order and criticality
            workflow_start_time: When workflow execution started
            execution_trace: Optional execution trace for detailed analysis
            
        Returns:
            AggregatedContext with all agent outputs and metadata
        """
        failure_handler = FailureHandler(execution_plan)
        agent_outputs: Dict[str, AgentOutput] = {}
        agent_statuses: Dict[str, str] = {}
        errors: Dict[str, Dict[str, Any]] = {}
        workflow_aborted = False
        aborted_at_agent = None
        
        # Process each agent in execution order
        for agent_id in execution_plan.execution_order:
            # Check if agent failed
            has_failed, error_message = failure_handler.check_agent_failure(agent_id, final_state)
            
            if has_failed:
                # Handle failure based on criticality
                should_abort, reason = failure_handler.handle_failure(agent_id, error_message)
                
                agent_statuses[agent_id] = "failure"
                errors[agent_id] = {
                    "code": "execution_failed",
                    "message": error_message,
                    "details": {"reason": reason}
                }
                
                # Create failure output
                agent_output = AgentOutput.failure(
                    agent_id=agent_id,
                    error_code="execution_failed",
                    error_message=error_message
                )
                
                if should_abort:
                    workflow_aborted = True
                    aborted_at_agent = agent_id
                    # Don't process remaining agents
                    # Mark remaining as skipped
                    remaining_agents = execution_plan.execution_order[
                        execution_plan.execution_order.index(agent_id) + 1:
                    ]
                    for remaining_id in remaining_agents:
                        agent_statuses[remaining_id] = "skipped"
                    break
            else:
                # Agent succeeded - extract output
                agent_statuses[agent_id] = "success"
                output_payload = self._extract_agent_output(agent_id, final_state)
                agent_output = AgentOutput.success(agent_id, output_payload)
                agent_outputs[agent_id] = agent_output
        
        # Calculate metadata
        workflow_duration = (datetime.utcnow() - workflow_start_time).total_seconds()
        metadata = {
            "workflow_start_time": workflow_start_time.isoformat(),
            "workflow_end_time": datetime.utcnow().isoformat(),
            "workflow_duration_seconds": workflow_duration,
            "total_agents_planned": len(execution_plan.agents),
            "agents_executed": len([s for s in agent_statuses.values() if s in ["success", "failure"]]),
            "agents_succeeded": len([s for s in agent_statuses.values() if s == "success"]),
            "agents_failed": len([s for s in agent_statuses.values() if s == "failure"]),
            "agents_skipped": len([s for s in agent_statuses.values() if s == "skipped"]),
            "failure_summary": failure_handler.get_failure_summary()
        }
        
        # Create aggregated context
        aggregated_context = AggregatedContext(
            agent_outputs=agent_outputs,
            agent_statuses=agent_statuses,
            errors=errors,
            metadata=metadata,
            criticality_info=execution_plan.criticality_map,
            execution_plan=execution_plan.model_dump(),
            workflow_aborted=workflow_aborted,
            aborted_at_agent=aborted_at_agent,
            partial_results_available=workflow_aborted and len(agent_outputs) > 0
        )
        
        return aggregated_context
    
    
    def _extract_agent_output(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract agent output from state."""
        output_field_map = {
            "market_analyst": "market_report",
            "fundamentals_analyst": "fundamentals_report",
            "information_analyst": "information_report",
            "bull_researcher": "investment_debate_state",
            "bear_researcher": "investment_debate_state",
            "research_manager": "investment_plan",
            "trader": "trader_investment_plan",
            "risky_debator": "risk_debate_state",
            "safe_debator": "risk_debate_state",
            "neutral_debator": "risk_debate_state",
            "risk_manager": "final_trade_decision",
        }
        
        output_field = output_field_map.get(agent_id)
        if output_field and output_field in state:
            return {output_field: state[output_field]}
        
        return {"state_snapshot": {k: v for k, v in state.items() 
                                   if isinstance(v, (str, int, float, bool, list, dict)) 
                                   and not k.startswith("_")}}

