"""
Agents service API endpoints.
"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


class ConversationMessage(BaseModel):
    """Message in conversation context for agents analysis."""
    id: str = Field(..., description="Message ID (format: msg-{uuid})")
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp in ISO format")
    metadata: Optional[dict] = Field(None, description="Optional message metadata")


class AgentAnalyzeRequest(BaseModel):
    """Request model for agents analysis endpoint."""
    company_name: str = Field(..., description="Company name or ticker symbol", min_length=1, max_length=100)
    trade_date: str = Field(..., description="Trade date in ISO format YYYY-MM-DD", pattern=r'^\d{4}-\d{2}-\d{2}$')
    conversation_context: Optional[List[ConversationMessage]] = Field(None, description="Optional conversation context")


class AgentAnalyzeResponse(BaseModel):
    """Response model for agents analysis endpoint."""
    company: str = Field(..., description="Company name or ticker")
    date: str = Field(..., description="Trade date")
    decision: str = Field(..., description="Trading decision: 'BUY', 'SELL', or 'HOLD'")
    state: dict = Field(..., description="Complete analysis state with all agent outputs and reports")


@router.post("/analyze", response_model=AgentAnalyzeResponse)
async def agents_analyze(request: AgentAnalyzeRequest):
    """
    Analyze a company using the agents service.
    Proxies request to agents service at AGENTS_SERVICE_URL/analyze
    
    Supports optional conversation_context for providing chat history to agents.
    """
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    analyze_endpoint = f"{agents_url}/analyze"
    
    payload = {
        "company_name": request.company_name,
        "trade_date": request.trade_date
    }
    
    if request.conversation_context:
        payload["conversation_context"] = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata
            }
            for msg in request.conversation_context
        ]
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(analyze_endpoint, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        error_detail = f"Agents service error: {e.response.status_code}"
        try:
            error_body = e.response.json()
            if "detail" in error_body:
                error_detail = f"Agents service error: {error_body['detail']}"
        except:
            error_detail = f"Agents service error: {e.response.text or str(e)}"
        
        raise HTTPException(
            status_code=e.response.status_code if e.response.status_code < 500 else 502,
            detail=error_detail
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Agents service unavailable: {str(e)}"
        )


@router.get("/health")
async def agents_health():
    """
    Agents health check endpoint.
    Returns status for agent backend.
    Uses AGENTS_SERVICE_URL environment variable (default: http://localhost:8001)
    """
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    health_endpoint = f"{agents_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_endpoint)
            response.raise_for_status()
            data = response.json()
            return {
                "status": "ok", 
                "agent_service": data,
                "agents_url": agents_url
            }
    except httpx.ConnectError as e:
        return {
            "status": "error",
            "message": f"Connection error: Could not reach agent service at {health_endpoint}",
            "error": str(e),
            "agents_url": agents_url
        }
    except httpx.TimeoutException as e:
        return {
            "status": "error",
            "message": f"Timeout: Agent service did not respond within 5 seconds",
            "error": str(e),
            "agents_url": agents_url
        }
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"HTTP error: Agent service returned {e.response.status_code}",
            "error": str(e),
            "agents_url": agents_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "agents_url": health_endpoint
        }

