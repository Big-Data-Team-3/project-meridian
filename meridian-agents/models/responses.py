"""
Response models for Meridian Agents Service API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""
    status: str = Field(..., description="Service status (ok or error)")
    service: str = Field(..., description="Service name")
    graph_initialized: bool = Field(..., description="Whether graph is initialized")
    error: Optional[str] = Field(None, description="Error message if status is error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "service": "meridian-agents",
                "graph_initialized": True
            }
        }


class AnalyzeResponse(BaseModel):
    """Response model for /analyze endpoint."""
    company: str = Field(..., description="Company name or ticker")
    date: str = Field(..., description="Trade date")
    decision: str = Field(..., description="Trading decision (BUY, SELL, HOLD)")
    state: Dict[str, Any] = Field(..., description="Complete graph state with all agent outputs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company": "AAPL",
                "date": "2024-12-19",
                "decision": "BUY",
                "state": {
                    "market_report": "...",
                    "fundamentals_report": "...",
                    "information_report": "..."
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type/class name")
    traceback: Optional[str] = Field(None, description="Stack trace (development only)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Analysis failed: Invalid company name",
                "error_type": "AnalysisError"
            }
        }

