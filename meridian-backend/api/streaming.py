"""
Streaming API endpoints for real-time agent trace updates.
Uses Server-Sent Events (SSE) to stream agent analysis progress.
"""
import asyncio
import datetime
import json
import logging
import os
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx

from api.auth import require_auth
from services.agent_orchestrator import get_agent_orchestrator
from services.message_service import MessageService
from models.query_intent import QueryIntent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


class AgentAnalysisRequest(BaseModel):
    """Request model for streaming agent analysis."""
    company_name: Optional[str] = Field(None, description="Company name or ticker symbol", min_length=1, max_length=100)
    trade_date: str = Field(..., description="Trade date in ISO format YYYY-MM-DD", pattern=r'^\d{4}-\d{2}-\d{2}$')
    query: Optional[str] = Field(None, description="User query text for intent classification")
    conversation_context: Optional[list] = Field(None, description="Optional conversation context")
    thread_id: Optional[str] = Field(None, description="Thread ID for saving agent response to database")


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
async def stream_agent_analysis(
    request: AgentAnalysisRequest,
    current_user: dict = Depends(require_auth)
):
    """
    Stream agent analysis in real-time using Server-Sent Events.

    This endpoint classifies the query intent, routes to appropriate agent workflow,
    and streams progress updates as Server-Sent Events. The client receives real-time
    updates about which agents are active, their progress, and final results.

    Returns:
        StreamingResponse with text/event-stream content type

    Example client usage:
        const eventSource = new EventSource('/api/streaming/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: 'Should I buy Apple stock?',
                company_name: 'AAPL',
                trade_date: '2024-12-19',
                conversation_context: [...]
            })
        });

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Agent update:', data);
        };
    """
    try:
        orchestrator = get_agent_orchestrator()
        
        # Extract query from conversation context or use provided query
        query_text = request.query
        if not query_text and request.conversation_context:
            # Get last user message from context
            user_messages = [msg for msg in request.conversation_context if msg.get("role") == "user"]
            if user_messages:
                query_text = user_messages[-1].get("content", "")
        
        # If no query and no company_name, we can't proceed
        if not query_text and not request.company_name:
            raise ValueError("Either 'query' or 'company_name' must be provided")
        
        # Use company_name as query fallback if no query provided
        if not query_text:
            query_text = f"Analyze {request.company_name}"
        
        # Classify query and get workflow
        intent, workflow = orchestrator.classify_and_get_workflow(
            query_text,
            request.conversation_context
        )
        
        # Get agent endpoint and timeout
        agent_endpoint, timeout_seconds = orchestrator.get_agent_endpoint(workflow)
        
        # If direct response (no agents), return early
        if workflow.workflow_type == "direct_response":
            async def direct_response_generator():
                start_event = AgentTraceEvent(
                    event_type="start",
                    message="Processing query directly (no agents required)",
                    timestamp=datetime.datetime.now().isoformat(),
                    data={"intent": intent.value, "workflow": workflow.workflow_type}
                )
                yield await format_sse_event(start_event)
                
                complete_event = AgentTraceEvent(
                    event_type="complete",
                    message="Query processed (direct response)",
                    progress=100,
                    timestamp=datetime.datetime.now().isoformat(),
                    data={"intent": intent.value}
                )
                yield await format_sse_event(complete_event)
            
            return StreamingResponse(
                direct_response_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                }
            )
        
        # For agent workflows, prepare request and route to agent service
        async def event_generator():
            final_response_text = None
            message_service = MessageService() if request.thread_id else None
            
            try:
                # Emit orchestration start event
                start_event = AgentTraceEvent(
                    event_type="orchestration_start",
                    message=f"Detected {intent.value} query, routing to {workflow.workflow_type}",
                    timestamp=datetime.datetime.now().isoformat(),
                    data={
                        "intent": intent.value,
                        "workflow": workflow.workflow_type,
                        "agents": workflow.agents,
                        "timeout_seconds": timeout_seconds,
                        "endpoint": agent_endpoint
                    }
                )
                yield await format_sse_event(start_event)
                
                # Prepare agent request payload
                agent_payload = orchestrator.prepare_agent_request(
                    company_name=request.company_name or "UNKNOWN",
                    trade_date=request.trade_date,
                    workflow=workflow,
                    conversation_context=request.conversation_context
                )
                
                # Use real agent service streaming endpoint
                agents_base_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
                
                # If using host.docker.internal or localhost, try container name (works if on same network)
                if "host.docker.internal" in agents_base_url or "localhost" in agents_base_url:
                    # Try container name - works when containers are on the same Docker network
                    # Fallback to original URL if container name doesn't work
                    container_name_url = "http://meridian-agents:8001"
                    logger.info(f"Detected localhost/host.docker.internal, will try container name: {container_name_url}")
                    agents_base_url = container_name_url
                
                agent_streaming_url = f"{agents_base_url}/analyze/stream"
                logger.info(f"Connecting to agent service at: {agent_streaming_url}")
                
                # Prepare request for agent service (use the prepared payload from orchestrator)
                # The orchestrator handles conversation_context format conversion
                agent_request = agent_payload
                
                try:
                    # Proxy the streaming response from the agent service
                    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                        async with client.stream("POST", agent_streaming_url, json=agent_request) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    # Parse the event to capture final response
                                    try:
                                        event_data = json.loads(line[6:])  # Remove "data: " prefix
                                        # Capture final response from complete events
                                        if event_data.get("event_type") in ["complete", "analysis_complete"]:
                                            if event_data.get("data") and isinstance(event_data["data"], dict):
                                                # Try to extract response text from various possible fields
                                                final_response_text = (
                                                    event_data["data"].get("response") or
                                                    event_data["data"].get("decision") or
                                                    event_data["data"].get("summary") or
                                                    event_data.get("message", "")
                                                )
                                    except (json.JSONDecodeError, KeyError):
                                        pass  # Continue streaming even if parsing fails
                                    
                                    yield line + "\n"
                                elif line.strip() and not line.startswith(":"):
                                    # Handle any other SSE format lines
                                    yield line + "\n"
                    
                    # Save agent response to database if thread_id is provided
                    if request.thread_id and final_response_text and message_service:
                        try:
                            assistant_msg = await message_service.save_assistant_message(
                                thread_id=request.thread_id,
                                content=final_response_text
                            )
                            logger.info(f"Saved agent response to thread {request.thread_id}: {assistant_msg['message_id']}")
                        except Exception as e:
                            logger.error(f"Failed to save agent response to database: {e}", exc_info=True)
                            # Don't fail the request if saving fails
                except httpx.HTTPStatusError as e:
                    error_detail = f"Agent service error: {e.response.status_code}"
                    try:
                        error_body = e.response.json()
                        if "detail" in error_body:
                            error_detail = f"Agent service error: {error_body['detail']}"
                    except:
                        error_detail = f"Agent service error: {e.response.text or str(e)}"
                    logger.error(f"HTTPStatusError from agent service: {error_detail}", exc_info=True)
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"Agent service failed: {error_detail}",
                        timestamp=datetime.datetime.now().isoformat()
                    )
                    yield await format_sse_event(error_event)
                except httpx.RequestError as e:
                    error_msg = str(e)
                    # Provide more helpful error message
                    if "Name or service not known" in error_msg or "Name resolution failed" in error_msg:
                        error_msg = f"Agent service hostname not resolvable. Check AGENTS_SERVICE_URL (current: {agents_base_url})"
                    elif "Connection refused" in error_msg:
                        error_msg = f"Agent service connection refused. Is the service running on {agents_base_url}?"
                    elif "timeout" in error_msg.lower():
                        error_msg = f"Agent service connection timeout. Service may be overloaded or unreachable at {agents_base_url}"
                    
                    logger.error(f"RequestError connecting to agent service at {agent_streaming_url}: {error_msg}", exc_info=True)
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"Agent service unavailable: {error_msg}",
                        timestamp=datetime.datetime.now().isoformat(),
                        data={
                            "agent_url": agent_streaming_url,
                            "error_type": type(e).__name__
                        }
                    )
                    yield await format_sse_event(error_event)
                except Exception as e:
                    logger.error(f"Unexpected error during agent streaming: {e}", exc_info=True)
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"An unexpected error occurred: {str(e)}",
                        timestamp=datetime.datetime.now().isoformat()
                    )
                    yield await format_sse_event(error_event)
                    
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
