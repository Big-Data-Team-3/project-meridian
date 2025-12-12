"""
Agent Executor

Wraps agent execution to catch exceptions and return standardized results.
"""

import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from agents_module.utils.output_schema import AgentOutput
from .models import AgentExecutionResult


class AgentExecutor:
    """
    Executes agents and wraps results in standardized format.
    
    Catches exceptions and converts them to AgentOutput with failure status.
    """
    
    def __init__(self):
        """Initialize the executor."""
        pass
    
    def execute_agent(
        self,
        agent_id: str,
        agent_node_func: Callable,
        state: Dict[str, Any],
        criticality: str = "non-critical"
    ) -> AgentExecutionResult:
        """
        Execute an agent node function and return standardized result.
        
        Args:
            agent_id: Agent identifier
            agent_node_func: Agent node function to execute
            state: Current graph state
            criticality: Agent criticality (critical or non-critical)
            
        Returns:
            AgentExecutionResult with execution outcome
        """
        start_time = datetime.utcnow()
        start_timestamp = time.time()
        
        try:
            # Execute agent node function
            result_state = agent_node_func(state)
            
            # Extract agent output from state
            # Try to find agent-specific report fields
            output_payload = self._extract_agent_output(agent_id, result_state)
            
            # Create successful AgentOutput
            agent_output = AgentOutput.success(
                agent_id=agent_id,
                payload=output_payload
            )
            
            end_time = datetime.utcnow()
            duration = time.time() - start_timestamp
            
            return AgentExecutionResult(
                agent_id=agent_id,
                status="success",
                output=agent_output,
                error=None,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                criticality=criticality,
                was_aborted=False
            )
            
        except Exception as e:
            # Agent execution failed
            end_time = datetime.utcnow()
            duration = time.time() - start_timestamp
            
            error_info = {
                "code": type(e).__name__,
                "message": str(e),
                "details": {
                    "agent_id": agent_id,
                    "criticality": criticality
                }
            }
            
            # Create failure AgentOutput
            agent_output = AgentOutput.failure(
                agent_id=agent_id,
                error_code=error_info["code"],
                error_message=error_info["message"],
                error_details=error_info["details"]
            )
            
            return AgentExecutionResult(
                agent_id=agent_id,
                status="failure",
                output=agent_output,
                error=error_info,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                criticality=criticality,
                was_aborted=False
            )
    
    def _extract_agent_output(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract agent-specific output from state.
        
        Args:
            agent_id: Agent identifier
            state: Result state from agent execution
            
        Returns:
            Dictionary with agent output payload
        """
        # Map agent IDs to their output fields in state
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
            return {
                output_field: state[output_field]
            }
        
        # Fallback: return relevant state fields
        return {
            "state_snapshot": {
                k: v for k, v in state.items() 
                if isinstance(v, (str, int, float, bool, list, dict)) and not k.startswith("_")
            }
        }

