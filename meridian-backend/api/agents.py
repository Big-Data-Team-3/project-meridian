"""
Agents service API endpoints.
"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
from fastapi.responses import Response
from utils.pdf_generator import generate_analysis_pdf

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
    decision: Optional[str] = Field(None, description="Trading decision: 'BUY', 'SELL', 'HOLD', or None for simple analysis queries")
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
    
    # Extract query from conversation context (last user message)
    query = None
    if request.conversation_context:
        user_messages = [msg for msg in request.conversation_context if msg.role == "user"]
        if user_messages:
            query = user_messages[-1].content
    
    payload = {
        "company_name": request.company_name,
        "trade_date": request.trade_date
    }
    
    # Add query if extracted
    if query:
        payload["query"] = query
    
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


@router.post("/pdf")
async def generate_pdf_from_results(request: AgentAnalyzeResponse):
    """
    Generate a PDF from existing analysis results.
    This endpoint accepts the analysis results that are displayed on screen
    and generates a PDF report without re-running the analysis.
    
    Use this when the user clicks the PDF download button on the frontend.
    """
    try:
        # Generate PDF from the provided results
        pdf_buffer = generate_analysis_pdf(
            company=request.company,
            date=request.date,
            decision=request.decision,
            state=request.state
        )
        
        # Return PDF as download
        filename = f"Meridian_{request.company}_{request.date}.pdf"
        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ImportError as e:
        if "reportlab" in str(e):
            raise HTTPException(
                status_code=503,
                detail="PDF generation is not available. Please install reportlab: pip install reportlab"
            )
        raise
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/pdf/{filename}")
async def download_pdf(filename: str):
    """
    Download a previously generated PDF report.
    
    Args:
        filename: Name of the PDF file to download (e.g., Meridian_MSFT_2025-01-15.pdf)
    
    Returns:
        PDF file as a downloadable response
    """
    try:
        import os
        pdf_dir = "/app/data/pdfs"
        pdf_path = os.path.join(pdf_dir, filename)
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF download error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download PDF: {str(e)}"
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

