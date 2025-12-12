"""
Agent Capability Registry Models

Defines the data models for agent capability descriptions.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgentCapability(BaseModel):
    """
    Structured description of an agent's capabilities and characteristics.
    
    This model is used by the LLM Planner to make informed decisions about
    agent selection and sequencing.
    """
    
    agent_id: str = Field(..., description="Unique identifier for the agent (e.g., 'market_analyst', 'fundamentals_analyst')")
    agent_name: str = Field(..., description="Human-readable name (e.g., 'Market Analyst', 'Fundamentals Analyst')")
    capabilities: List[str] = Field(..., description="List of what the agent can do")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema defining required inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema defining output format")
    execution_time_estimate: float = Field(..., description="Typical execution time in seconds", ge=0)
    cost_estimate: Optional[float] = Field(None, description="Estimated token/API cost (if applicable)", ge=0)
    dependencies: List[str] = Field(default_factory=list, description="List of agent_ids that must run before this agent")
    criticality_default: str = Field("non-critical", description="Default criticality level: 'critical' or 'non-critical'")
    
    # Optional metadata
    description: Optional[str] = Field(None, description="Detailed description of the agent's purpose")
    tools: Optional[List[str]] = Field(None, description="List of tools/data sources the agent uses")
    model_requirements: Optional[str] = Field(None, description="LLM model requirements (e.g., 'gpt-4o', 'gpt-4o-mini')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "market_analyst",
                "agent_name": "Market Analyst",
                "capabilities": [
                    "Technical analysis",
                    "Chart pattern recognition",
                    "Indicator calculation"
                ],
                "input_schema": {
                    "type": "object",
                    "required": ["company_of_interest", "trade_date"],
                    "properties": {
                        "company_of_interest": {"type": "string"},
                        "trade_date": {"type": "string", "format": "date"}
                    }
                },
                "output_schema": {
                    "type": "object",
                    "required": ["agent_id", "status", "payload"],
                    "properties": {
                        "agent_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["success", "failure", "partial"]},
                        "payload": {
                            "type": "object",
                            "properties": {
                                "market_report": {"type": "string"}
                            }
                        }
                    }
                },
                "execution_time_estimate": 45.0,
                "cost_estimate": 0.05,
                "dependencies": [],
                "criticality_default": "critical"
            }
        }

