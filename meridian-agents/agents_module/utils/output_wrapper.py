"""
Output Wrapper Utility

Provides utilities to wrap existing agent functions to ensure they
return outputs conforming to the common AgentOutput schema.
"""

from typing import Dict, Any, Callable, Optional
from .output_schema import AgentOutput, AgentError


def wrap_agent_output(
    agent_id: str,
    agent_node_func: Callable,
    output_field: str,
    error_field: Optional[str] = None
) -> Callable:
    """
    Wrap an agent node function to ensure it returns AgentOutput-compatible state.
    
    This wrapper:
    1. Calls the original agent function
    2. Extracts the output from the specified field
    3. Wraps it in AgentOutput format
    4. Stores the AgentOutput in state for orchestrator to use
    
    Args:
        agent_id: Agent identifier
        agent_node_func: Original agent node function
        output_field: Field name in state where agent output is stored (e.g., "market_report")
        error_field: Optional field name for error information
        
    Returns:
        Wrapped agent node function that ensures AgentOutput format
    """
    def wrapped_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapped node function that ensures AgentOutput format.
        
        Args:
            state: Graph state
            
        Returns:
            Updated state with AgentOutput stored in agent_outputs field
        """
        try:
            # Call original agent function
            result_state = agent_node_func(state)
            
            # Extract output from specified field
            output_value = result_state.get(output_field, "")
            
            # Determine status
            if error_field and error_field in result_state:
                # Agent reported an error
                error_info = result_state[error_field]
                status = "failure" if not output_value else "partial"
                agent_output = AgentOutput(
                    agent_id=agent_id,
                    status=status,
                    payload={output_field: output_value} if output_value else {},
                    error=AgentError(
                        code="agent_error",
                        message=str(error_info),
                        details={}
                    ) if status != "success" else None
                )
            elif output_value and isinstance(output_value, str) and output_value.strip():
                # Success - has output
                agent_output = AgentOutput.success(
                    agent_id=agent_id,
                    payload={output_field: output_value}
                )
            elif output_value and isinstance(output_value, dict):
                # Success - dict output
                agent_output = AgentOutput.success(
                    agent_id=agent_id,
                    payload=output_value
                )
            else:
                # Partial or failure - empty output
                agent_output = AgentOutput.partial(
                    agent_id=agent_id,
                    payload={output_field: output_value} if output_value else {},
                    error_code="empty_output",
                    error_message=f"Agent {agent_id} produced empty output"
                )
            
            # Store AgentOutput in state
            # The orchestrator will extract this later
            if "agent_outputs" not in result_state:
                result_state["agent_outputs"] = {}
            result_state["agent_outputs"][agent_id] = agent_output
            
            return result_state
            
        except Exception as e:
            # Agent execution failed
            error_output = AgentOutput.failure(
                agent_id=agent_id,
                error_code=type(e).__name__,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )
            
            # Store error output in state
            if "agent_outputs" not in state:
                state["agent_outputs"] = {}
            state["agent_outputs"][agent_id] = error_output
            
            # Also preserve original error in state
            if output_field:
                state[output_field] = f"Error: {str(e)}"
            
            return state
    
    return wrapped_node


def ensure_agent_output_format(
    state: Dict[str, Any],
    agent_id: str,
    output_field: str
) -> AgentOutput:
    """
    Ensure agent output in state conforms to AgentOutput format.
    
    This is a helper function that can be called by agents to convert
    their output to AgentOutput format before returning state.
    
    Args:
        state: Graph state
        agent_id: Agent identifier
        output_field: Field name where output is stored
        
    Returns:
        AgentOutput instance
    """
    output_value = state.get(output_field, "")
    
    if isinstance(output_value, str):
        if output_value.strip() and not output_value.lower().startswith("error"):
            return AgentOutput.success(
                agent_id=agent_id,
                payload={output_field: output_value}
            )
        else:
            return AgentOutput.failure(
                agent_id=agent_id,
                error_code="empty_or_error_output",
                error_message=f"Agent {agent_id} produced empty or error output"
            )
    elif isinstance(output_value, dict):
        return AgentOutput.success(
            agent_id=agent_id,
            payload=output_value
        )
    else:
        return AgentOutput.partial(
            agent_id=agent_id,
            payload={output_field: str(output_value) if output_value else ""},
            error_code="unexpected_output_type",
            error_message=f"Agent {agent_id} produced unexpected output type"
        )

