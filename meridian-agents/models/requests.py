"""
Request models for Meridian Agents Service API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ConversationMessage(BaseModel):
    """Message in conversation context."""
    id: str = Field(..., description="Message ID (format: msg-{uuid})")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint."""
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name or ticker symbol"
    )
    trade_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Trade date (ISO format: YYYY-MM-DD)"
    )
    query: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional user query for dynamic agent selection. If not provided, will be extracted from conversation_context or generated from company_name."
    )
    conversation_context: Optional[List[ConversationMessage]] = Field(
        None,
        max_items=50,
        description="Optional conversation context (last N messages, max 50)"
    )
    selective_agents: Optional[List[str]] = Field(
        None,
        description="Optional list of agents to use (for selective workflows). If provided, only these agents will be used."
    )
    
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Validate company name format."""
        if not v or not v.strip():
            raise ValueError("company_name cannot be empty")
        # Remove whitespace
        return v.strip().upper()
    
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """Validate trade date format."""
        import re
        from datetime import datetime
        
        # Check format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("trade_date must be in YYYY-MM-DD format")
        
        # Check if valid date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date: {v}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "AAPL",
                "trade_date": "2024-12-19",
                "conversation_context": [
                    {
                        "id": "msg-12345678",
                        "role": "user",
                        "content": "What about Apple?",
                        "timestamp": "2024-12-19T10:00:00Z"
                    }
                ]
            }
        }


class SingleAgentRequest(BaseModel):
    """Request model for single-agent analysis endpoint."""
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name or ticker symbol"
    )
    trade_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Trade date (ISO format: YYYY-MM-DD)"
    )
    conversation_context: Optional[List[ConversationMessage]] = Field(
        None,
        max_items=50,
        description="Optional conversation context (last N messages, max 50)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "AAPL",
                "trade_date": "2024-12-19",
                "conversation_context": []
            }
        }


class MultiAgentRequest(BaseModel):
    """Request model for multi-agent analysis endpoint."""
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name or ticker symbol"
    )
    trade_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Trade date (ISO format: YYYY-MM-DD)"
    )
    agents: List[str] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="List of agent types to include: 'market', 'fundamentals', 'information'"
    )
    conversation_context: Optional[List[ConversationMessage]] = Field(
        None,
        max_items=50,
        description="Optional conversation context (last N messages, max 50)"
    )
    include_debate: bool = Field(
        default=False,
        description="Whether to include debate phase (default: False)"
    )
    include_risk: bool = Field(
        default=False,
        description="Whether to include risk analysis (default: False)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "AAPL",
                "trade_date": "2024-12-19",
                "agents": ["market", "fundamentals"],
                "include_debate": False,
                "include_risk": False
            }
        }


class FocusedAnalysisRequest(BaseModel):
    """Request model for focused analysis endpoint."""
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name or ticker symbol"
    )
    trade_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Trade date (ISO format: YYYY-MM-DD)"
    )
    focus: str = Field(
        ...,
        description="Focus area: 'sentiment_only', 'technical_only', 'fundamental_only'"
    )
    conversation_context: Optional[List[ConversationMessage]] = Field(
        None,
        max_items=50,
        description="Optional conversation context (last N messages, max 50)"
    )


class SelectiveAnalysisRequest(BaseModel):
    """Request model for selective analysis endpoint."""
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company name or ticker symbol"
    )
    trade_date: str = Field(
        ...,
        pattern=r'^\d{4}-\d{2}-\d{2}$',
        description="Trade date (ISO format: YYYY-MM-DD)"
    )
    selective_agents: List[str] = Field(
        ...,
        min_items=1,
        max_items=20,
        description="List of specific agents to run"
    )
    include_debate: bool = Field(
        False,
        description="Whether to include debate phase with researchers"
    )
    include_risk: bool = Field(
        False,
        description="Whether to include risk analysis phase"
    )
    conversation_context: Optional[List[ConversationMessage]] = Field(
        None,
        max_items=50,
        description="Optional conversation context (last N messages, max 50)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "AAPL",
                "trade_date": "2024-12-19",
                "focus": "sentiment_only",
                "conversation_context": []
            }
        }

