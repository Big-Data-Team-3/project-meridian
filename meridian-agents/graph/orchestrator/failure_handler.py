"""
Failure Handler

Handles critical vs non-critical agent failures during graph execution.
"""

from typing import Dict, List, Any, Optional, Tuple
from ..planner.models import ExecutionPlan
from agents_module.utils.output_schema import AgentOutput


class FailureHandler:
    """
    Handles agent failures based on criticality.
    
    Detects failures, checks criticality, and decides whether to abort
    workflow or continue with remaining agents.
    """
    
    def __init__(self, execution_plan: ExecutionPlan):
        """
        Initialize failure handler.
        
        Args:
            execution_plan: Execution plan with criticality information
        """
        self.execution_plan = execution_plan
        self.failed_agents: List[str] = []
        self.critical_failures: List[str] = []
    
    def check_agent_failure(
        self,
        agent_id: str,
        state: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an agent failed based on state.
        
        Args:
            agent_id: Agent identifier
            state: Graph state after agent execution
            
        Returns:
            Tuple of (has_failed, error_message)
        """
        # Map agent IDs to their expected output fields
        # For information_analyst, check multiple fields (it writes to all for backward compatibility)
        output_field_map = {
            "market_analyst": "market_report",
            "fundamentals_analyst": "fundamentals_report",
            "information_analyst": "information_report",  # Primary field
            "bull_researcher": "investment_debate_state",
            "bear_researcher": "investment_debate_state",
            "research_manager": "investment_plan",
            "trader": "trader_investment_plan",
            "risky_debator": "risk_debate_state",
            "safe_debator": "risk_debate_state",
            "neutral_debator": "risk_debate_state",
            "risk_manager": "final_trade_decision",
        }
        
        # Fallback fields for agents that write to multiple fields
        fallback_field_map = {
            "information_analyst": ["news_report", "sentiment_report"],  # information_analyst writes to these too
        }
        
        # Normalize agent_id (remove _analyst suffix for matching)
        normalized_id = agent_id.replace("_analyst", "").replace("_debator", "").replace("_researcher", "")
        field_key = None
        
        for key, field in output_field_map.items():
            if key.startswith(normalized_id) or normalized_id in key:
                field_key = field
                break
        
        if not field_key:
            # Try direct match
            field_key = output_field_map.get(agent_id)
        
        if field_key:
            # Check primary field first
            if field_key in state:
                field_value = state[field_key]
                # Check if field has meaningful content
                if isinstance(field_value, str):
                    if not field_value.strip() or "error" in field_value.lower():
                        print(f"⚠️ Failure detected for {agent_id}: field '{field_key}' is empty or contains error")
                        return True, f"Agent {agent_id} produced empty or error output"
                elif isinstance(field_value, dict):
                    if not field_value:
                        print(f"⚠️ Failure detected for {agent_id}: field '{field_key}' is empty dict")
                        return True, f"Agent {agent_id} produced empty output"
                else:
                    # Field exists and has content - success
                    print(f"✅ Success for {agent_id}: field '{field_key}' found with content (type: {type(field_value).__name__})")
                    return False, None  # Success
            else:
                # Primary field not found - check fallback fields
                fallback_fields = fallback_field_map.get(agent_id, [])
                for fallback_field in fallback_fields:
                    if fallback_field in state:
                        fallback_value = state[fallback_field]
                        if isinstance(fallback_value, str) and fallback_value.strip() and "error" not in fallback_value.lower():
                            print(f"✅ Success for {agent_id}: fallback field '{fallback_field}' found with content")
                            return False, None  # Success
                        elif isinstance(fallback_value, dict) and fallback_value:
                            print(f"✅ Success for {agent_id}: fallback field '{fallback_field}' found with content")
                            return False, None  # Success
                
                # Neither primary nor fallback fields found - failure
                available_fields = [k for k in state.keys() if not k.startswith("_") and k not in ["messages", "sender"]]
                print(f"❌ Failure detected for {agent_id}: field '{field_key}' not found in state. Available fields: {available_fields[:10]}")
                return True, f"Agent {agent_id} output field {field_key} not found in state"
        
        return False, None
    
    def handle_failure(
        self,
        agent_id: str,
        error_message: str
    ) -> Tuple[bool, str]:
        """
        Handle agent failure based on criticality.
        
        Args:
            agent_id: Failed agent identifier
            error_message: Error message
            
        Returns:
            Tuple of (should_abort, reason)
        """
        self.failed_agents.append(agent_id)
        
        criticality = self.execution_plan.criticality_map.get(agent_id, "non-critical")
        
        if criticality == "critical":
            self.critical_failures.append(agent_id)
            return True, f"Critical agent {agent_id} failed: {error_message}"
        else:
            return False, f"Non-critical agent {agent_id} failed: {error_message}. Continuing workflow."
    
    def should_abort_workflow(self) -> bool:
        """Check if workflow should be aborted due to critical failures."""
        return len(self.critical_failures) > 0
    
    def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of failures."""
        return {
            "failed_agents": self.failed_agents,
            "critical_failures": self.critical_failures,
            "non_critical_failures": [
                agent_id for agent_id in self.failed_agents 
                if agent_id not in self.critical_failures
            ],
            "workflow_aborted": self.should_abort_workflow()
        }

