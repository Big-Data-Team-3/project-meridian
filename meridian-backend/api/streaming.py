"""
Streaming API endpoints for real-time agent trace updates.
Uses Server-Sent Events (SSE) to stream agent analysis progress.
"""
import asyncio
import datetime
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx

from api.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


class AgentAnalysisRequest(BaseModel):
    """Request model for streaming agent analysis."""
    company_name: str = Field(..., description="Company name or ticker symbol", min_length=1, max_length=100)
    trade_date: str = Field(..., description="Trade date in ISO format YYYY-MM-DD", pattern=r'^\d{4}-\d{2}-\d{2}$')
    conversation_context: Optional[list] = Field(None, description="Optional conversation context")


class AgentTraceEvent(BaseModel):
    """Model for agent trace events sent via SSE."""
    event_type: str = Field(..., description="Type of event: 'start', 'progress', 'agent_update', 'complete', 'error'")
    agent_name: Optional[str] = Field(None, description="Name of the agent currently active")
    message: str = Field(..., description="Human-readable status message")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)", ge=0, le=100)
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")
    timestamp: str = Field(..., description="Event timestamp in ISO format")


async def format_sse_event(event: AgentTraceEvent) -> str:
    """Format an event as Server-Sent Events data."""
    event_data = {
        "event_type": event.event_type,
        "agent_name": event.agent_name,
        "message": event.message,
        "progress": event.progress,
        "data": event.data,
        "timestamp": event.timestamp
    }

    # Remove None values to keep payload clean
    event_data = {k: v for k, v in event_data.items() if v is not None}

    return f"data: {json.dumps(event_data)}\n\n"


async def mock_agent_analysis_stream(company_name: str, trade_date: str) -> AsyncGenerator[str, None]:
    """
    Mock agent analysis that simulates real-time streaming.
    In production, this would connect to your actual agent service.
    """
    import datetime
    import random

    agents = [
        {"name": "Market Analyst", "duration": 15, "steps": ["Gathering market data", "Analyzing trends", "Calculating metrics"]},
        {"name": "Fundamental Analyst", "duration": 20, "steps": ["Reviewing financials", "Analyzing ratios", "Assessing valuation"]},
        {"name": "Information Analyst", "duration": 12, "steps": ["Scanning news", "Evaluating sentiment", "Identifying catalysts"]},
        {"name": "Risk Manager", "duration": 8, "steps": ["Assessing volatility", "Evaluating position sizing", "Calculating risk metrics"]},
    ]

    # Send start event
    start_event = AgentTraceEvent(
        event_type="start",
        message=f"Starting analysis for {company_name} on {trade_date}",
        timestamp=datetime.datetime.now().isoformat()
    )
    yield await format_sse_event(start_event)

    total_progress = 0
    progress_increment = 100 // len(agents)

    for agent in agents:
        # Agent start event
        agent_start = AgentTraceEvent(
            event_type="agent_update",
            agent_name=agent["name"],
            message=f"{agent['name']} is now analyzing {company_name}",
            progress=total_progress,
            timestamp=datetime.datetime.now().isoformat()
        )
        yield await format_sse_event(agent_start)

        # Simulate agent working through steps
        step_progress = progress_increment // len(agent["steps"])
        current_agent_progress = 0

        for step in agent["steps"]:
            await asyncio.sleep(random.uniform(1, 3))  # Simulate processing time

            current_agent_progress += step_progress
            total_progress += step_progress

            progress_event = AgentTraceEvent(
                event_type="progress",
                agent_name=agent["name"],
                message=f"{agent['name']}: {step}",
                progress=min(total_progress, 95),  # Cap at 95% until completion
                timestamp=datetime.datetime.now().isoformat()
            )
            yield await format_sse_event(progress_event)

        # Brief pause between agents
        await asyncio.sleep(0.5)

    # Final completion
    await asyncio.sleep(1)
    complete_event = AgentTraceEvent(
        event_type="complete",
        message=f"Analysis complete for {company_name}",
        progress=100,
        data={
            "decision": random.choice(["BUY", "SELL", "HOLD"]),
            "confidence": random.uniform(0.6, 0.95),
            "agents_used": [agent["name"] for agent in agents]
        },
        timestamp=datetime.datetime.now().isoformat()
    )
    yield await format_sse_event(complete_event)


async def real_agent_analysis_stream(company_name: str, trade_date: str, conversation_context: Optional[list] = None) -> AsyncGenerator[str, None]:
    """
    Real agent analysis streaming that connects to the agents service.
    This would replace the mock version in production.
    """
    import datetime
    import os

    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")

    try:
        # Send start event
        start_event = AgentTraceEvent(
            event_type="start",
            message=f"Starting agent analysis for {company_name}",
            timestamp=datetime.datetime.now().isoformat()
        )
        yield await format_sse_event(start_event)

        # Prepare request payload
        payload = {
            "company_name": company_name,
            "trade_date": trade_date
        }
        if conversation_context:
            payload["conversation_context"] = conversation_context

        # For now, we'll call the regular agents endpoint
        # In the future, you might want to modify the agents service to support streaming
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minute timeout
            response = await client.post(f"{agents_url}/analyze", json=payload)
            response.raise_for_status()
            result = response.json()

        # Send completion event with results
        complete_event = AgentTraceEvent(
            event_type="complete",
            message=f"Agent analysis completed for {company_name}",
            progress=100,
            data={
                "decision": result.get("decision"),
                "company": result.get("company"),
                "date": result.get("date"),
                "state": result.get("state"),
                "agents_used": ["Market Analyst", "Fundamental Analyst", "Information Analyst", "Risk Manager"]  # Placeholder
            },
            timestamp=datetime.datetime.now().isoformat()
        )
        yield await format_sse_event(complete_event)

    except Exception as e:
        logger.error(f"Agent analysis streaming error: {e}", exc_info=True)
        error_event = AgentTraceEvent(
            event_type="error",
            message=f"Analysis failed: {str(e)}",
            timestamp=datetime.datetime.now().isoformat()
        )
        yield await format_sse_event(error_event)


@router.post("/analyze")
async def stream_agent_analysis(request: AgentAnalysisRequest):
    """
    Stream agent analysis in real-time using Server-Sent Events.

    This endpoint starts an agent analysis and streams progress updates
    as Server-Sent Events. The client receives real-time updates about
    which agents are active, their progress, and final results.

    Returns:
        StreamingResponse with text/event-stream content type

    Example client usage:
        const eventSource = new EventSource('/api/streaming/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company_name: 'AAPL',
                trade_date: '2024-12-19'
            })
        });

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Agent update:', data);
        };
    """
    try:
        # For development/testing, use mock streaming
        # In production, switch to real_agent_analysis_stream
        async def event_generator():
            try:
                async for event in mock_agent_analysis_stream(
                    request.company_name,
                    request.trade_date
                ):
                    yield event
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_event = AgentTraceEvent(
                    event_type="error",
                    message=f"Streaming failed: {str(e)}",
                    timestamp=datetime.datetime.now().isoformat()
                )
                yield await format_sse_event(error_event)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )

    except Exception as e:
        logger.error(f"Failed to start streaming analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start agent analysis streaming: {str(e)}"
        )


@router.get("/health")
async def streaming_health():
    """
    Health check for streaming service.

    Returns:
        dict: Health status information
    """
    return {
        "status": "ok",
        "service": "streaming",
        "features": ["sse", "agent_analysis_streaming"],
        "version": "1.0.0"
    }
