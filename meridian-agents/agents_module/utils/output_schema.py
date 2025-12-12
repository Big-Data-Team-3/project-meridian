"""
Common Agent Output Schema

All agents must return outputs conforming to this standardized schema
to enable reliable aggregation and synthesis.
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ValidationError


class AgentError(BaseModel):
    """Error information for agent failures."""
    
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class AgentOutput(BaseModel):
    """
    Standardized output schema for all agents.
    
    Every agent MUST return output in this format to enable:
    - Reliable aggregation by the orchestrator
    - Consistent error handling
    - Final synthesis by the synthesizer
    """
    
    agent_id: str = Field(..., description="Unique identifier of the agent that produced this output")
    status: Literal["success", "failure", "partial"] = Field(
        ..., 
        description="Execution status: success (completed), failure (error), partial (some output but issues)"
    )
    payload: Dict[str, Any] = Field(
        ..., 
        description="Agent-specific output data. Must conform to agent's declared output schema."
    )
    error: Optional[AgentError] = Field(
        None, 
        description="Error information. Only present if status is 'failure' or 'partial'"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "market_analyst",
                "status": "success",
                "payload": {
                    "market_report": "Detailed technical analysis report...",
                    "indicators_used": ["rsi", "macd", "boll_ub"]
                },
                "error": None
            }
        }
    
    @classmethod
    def success(cls, agent_id: str, payload: Dict[str, Any]) -> "AgentOutput":
        """
        Create a successful agent output.
        
        Args:
            agent_id: Agent identifier
            payload: Agent output data
            
        Returns:
            AgentOutput with status="success"
        """
        return cls(agent_id=agent_id, status="success", payload=payload)
    
    @classmethod
    def failure(cls, agent_id: str, error_code: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> "AgentOutput":
        """
        Create a failed agent output.
        
        Args:
            agent_id: Agent identifier
            error_code: Error code
            error_message: Error message
            error_details: Additional error details
            
        Returns:
            AgentOutput with status="failure"
        """
        return cls(
            agent_id=agent_id,
            status="failure",
            payload={},
            error=AgentError(code=error_code, message=error_message, details=error_details or {})
        )
    
    @classmethod
    def partial(cls, agent_id: str, payload: Dict[str, Any], error_code: str, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> "AgentOutput":
        """
        Create a partial agent output (some data but with issues).
        
        Args:
            agent_id: Agent identifier
            payload: Partial output data
            error_code: Error code
            error_message: Error message
            error_details: Additional error details
            
        Returns:
            AgentOutput with status="partial"
        """
        return cls(
            agent_id=agent_id,
            status="partial",
            payload=payload,
            error=AgentError(code=error_code, message=error_message, details=error_details or {})
        )


def validate_agent_output(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[AgentOutput]]:
    """
    Validate that data conforms to AgentOutput schema.
    
    Args:
        data: Dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message, validated_output)
        - is_valid: True if valid, False otherwise
        - error_message: Error message if invalid, None otherwise
        - validated_output: AgentOutput instance if valid, None otherwise
    """
    try:
        output = AgentOutput(**data)
        return True, None, output
    except ValidationError as e:
        error_msg = f"AgentOutput validation failed: {str(e)}"
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Unexpected error validating AgentOutput: {str(e)}"
        return False, error_msg, None


def validate_agent_outputs(outputs: list[Dict[str, Any]]) -> tuple[list[AgentOutput], list[str]]:
    """
    Validate multiple agent outputs.
    
    Args:
        outputs: List of dictionaries to validate
        
    Returns:
        Tuple of (valid_outputs, error_messages)
        - valid_outputs: List of validated AgentOutput instances
        - error_messages: List of error messages for invalid outputs
    """
    valid_outputs = []
    error_messages = []
    
    for idx, output_data in enumerate(outputs):
        is_valid, error_msg, validated = validate_agent_output(output_data)
        if is_valid and validated:
            valid_outputs.append(validated)
        else:
            error_messages.append(f"Output {idx}: {error_msg}")
    
    return valid_outputs, error_messages

