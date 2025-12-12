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
from httpx import Timeout

logger = logging.getLogger(__name__)

# Import yfinance for ticker validation (optional - only used if available)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available - ticker validation will be skipped")

from api.auth import require_auth
from services.agent_orchestrator import get_agent_orchestrator
from services.message_service import MessageService
from models.query_intent import QueryIntent
from utils.pdf_generator import generate_analysis_pdf

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def validate_company_ticker(company_name: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that a company/ticker exists and can be fetched from data sources.
    
    Args:
        company_name: Company name or ticker symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message, normalized_ticker)
        - is_valid: True if company exists and can be fetched
        - error_message: Error message if validation fails, None if valid
        - normalized_ticker: The actual ticker symbol from yfinance (e.g., "AAPL"), or None if invalid
    """
    if not company_name or company_name.strip() == "" or company_name == "UNKNOWN":
        return False, "No company or ticker symbol provided. Please specify a company name or stock ticker symbol (e.g., AAPL, TSLA, MSFT).", None
    
    company_name = company_name.strip().upper()
    
    # If yfinance is available, validate the ticker
    if YFINANCE_AVAILABLE:
        try:
            # Note: yfinance uses requests library which has default timeouts
            # If validation takes too long, it will raise an exception which we catch below
            ticker = yf.Ticker(company_name)
            info = ticker.info
            
            # Check if ticker is valid (has symbol)
            if not info or not info.get('symbol'):
                return False, (
                    f"Company or ticker '{company_name}' not found in our data sources. "
                    "Please provide a valid stock ticker symbol (e.g., AAPL for Apple, TSLA for Tesla, MSFT for Microsoft)."
                ), None
            
            # More lenient check: if we have a symbol, accept it even without name fields
            # This handles edge cases like new IPOs or international tickers
            # Only reject if we have absolutely no useful data
            symbol = info.get('symbol')
            has_name = info.get('shortName') or info.get('longName')
            
            if symbol:
                # If we have a symbol, accept it (even without name)
                # This is more lenient and handles edge cases better
                # Return the normalized ticker symbol (uppercase) for consistency
                normalized_ticker = symbol.upper() if symbol else None
                company_display = has_name or symbol
                logger.info(f"✓ Validated company: {company_display} ({normalized_ticker})")
                return True, None, normalized_ticker
            else:
                # No symbol means invalid ticker
                return False, (
                    f"Company or ticker '{company_name}' not found in our data sources. "
                    "Please provide a valid stock ticker symbol (e.g., AAPL for Apple, TSLA for Tesla, MSFT for Microsoft)."
                ), None
            
        except Exception as e:
            logger.warning(f"Error validating ticker {company_name}: {e}")
            # Check if it's a timeout or network error
            error_str = str(e).lower()
            if 'timeout' in error_str or 'timed out' in error_str:
                return False, (
                    f"Validation timeout for '{company_name}'. "
                    "The data source is taking too long to respond. Please try again."
                ), None
            elif 'connection' in error_str or 'network' in error_str:
                return False, (
                    f"Network error while validating '{company_name}'. "
                    "Please check your connection and try again."
                ), None
            else:
                return False, (
                    f"Unable to validate company '{company_name}'. "
                    "Please check if the ticker symbol is correct and try again."
                ), None
    else:
        # If yfinance not available, do basic format check
        # Allow it to proceed but log a warning
        if len(company_name) > 5 or not company_name.isalpha():
            return False, (
                f"Invalid ticker format: '{company_name}'. "
                "Ticker symbols are typically 1-5 uppercase letters (e.g., AAPL, TSLA)."
            ), None
        
        logger.warning("yfinance not available - skipping ticker validation")
        # Return the uppercased input as normalized ticker (best we can do without yfinance)
        return True, None, company_name


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
        timestamp=get_utc_timestamp()
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
            timestamp=get_utc_timestamp()
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
                timestamp=get_utc_timestamp()
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
        timestamp=get_utc_timestamp()
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
            timestamp=get_utc_timestamp()
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
            timestamp=get_utc_timestamp()
        )
        yield await format_sse_event(complete_event)

    except Exception as e:
        logger.error(f"Agent analysis streaming error: {e}", exc_info=True)
        error_event = AgentTraceEvent(
            event_type="error",
            message=f"Analysis failed: {str(e)}",
            timestamp=get_utc_timestamp()
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
        
        # Classify query and get workflow (also get full classification for entity extraction)
        intent, workflow = orchestrator.classify_and_get_workflow(
            query_text,
            request.conversation_context
        )
        
        # Extract company ticker from LLM entities if not provided
        extracted_ticker = None
        if not request.company_name:
            try:
                classification_result = orchestrator.classifier.classify_with_entities(
                    query_text,
                    request.conversation_context
                )
                
                if classification_result and classification_result.entities:
                    # Look for ticker-like entities (1-5 uppercase letters)
                    for entity in classification_result.entities:
                        entity_upper = entity.upper().strip()
                        # Check if it looks like a ticker (1-5 uppercase letters, no spaces)
                        if 1 <= len(entity_upper) <= 5 and entity_upper.isalpha() and ' ' not in entity_upper:
                            # Validate with yfinance if available (quick check)
                            if YFINANCE_AVAILABLE:
                                try:
                                    ticker = yf.Ticker(entity_upper)
                                    info = ticker.info
                                    # Check if ticker is valid (has symbol in info)
                                    if info and info.get('symbol'):
                                        extracted_ticker = entity_upper
                                        logger.info(f"✓ Extracted and validated ticker '{extracted_ticker}' from query entities")
                                        break
                                except Exception as e:
                                    logger.debug(f"Ticker validation failed for {entity_upper}: {e}")
                                    continue
                            else:
                                # If yfinance not available, use entity as-is if it looks like a ticker
                                extracted_ticker = entity_upper
                                logger.info(f"✓ Extracted ticker '{extracted_ticker}' from query entities (validation skipped)")
                                break
            except Exception as e:
                logger.warning(f"Failed to extract ticker from entities: {e}")
        
        # Use extracted ticker, provided company_name, or fallback
        final_company_name = extracted_ticker or request.company_name or "UNKNOWN"
        
        # Validate company/ticker before proceeding with agent workflows
        # Only validate if workflow requires agents (not for direct_response)
        if workflow.workflow_type != "direct_response":
            # Validate company exists and can be fetched
            is_valid, error_message, normalized_ticker = validate_company_ticker(final_company_name)
            
            if not is_valid:
                logger.warning(f"Company validation failed: {error_message} (company: {final_company_name})")
                
                # Return error early - don't start agent workflow
                async def error_generator():
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=error_message or "Invalid company or ticker symbol",
                        timestamp=datetime.datetime.now().isoformat(),
                        data={
                            "error_type": "invalid_company",
                            "company_name": final_company_name,
                            "suggestion": (
                                f"'{final_company_name}' was not found in our data sources. "
                                "Please try:\n"
                                "- Using the stock ticker symbol (e.g., AAPL for Apple, TSLA for Tesla, MSFT for Microsoft)\n"
                                "- Checking the spelling of the company name\n"
                                "- Using the full company name"
                            )
                        }
                    )
                    yield await format_sse_event(error_event)
                    
                    # Send complete event so frontend knows to stop
                    complete_event = AgentTraceEvent(
                        event_type="complete",
                        message="Workflow stopped - invalid company",
                        progress=0,
                        timestamp=datetime.datetime.now().isoformat(),
                        data={"error": True, "stopped": True}
                    )
                    yield await format_sse_event(complete_event)
                
                return StreamingResponse(
                    error_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Cache-Control",
                    }
                )
            
            # Use normalized ticker if available (from yfinance validation)
            # This ensures agents receive the correct ticker symbol (e.g., "AAPL") 
            # instead of company name (e.g., "APPLE")
            if normalized_ticker:
                final_company_name = normalized_ticker
                logger.info(f"✓ Using normalized ticker: {final_company_name} (original: {request.company_name or extracted_ticker})")
        
        # Get agent endpoint and timeout
        agent_endpoint, timeout_seconds = orchestrator.get_agent_endpoint(workflow)
        
        # If direct response (no agents), return early
        if workflow.workflow_type == "direct_response":
            async def direct_response_generator():
                start_event = AgentTraceEvent(
                    event_type="start",
                    message="Processing query directly (no agents required)",
                    timestamp=get_utc_timestamp(),
                    data={"intent": intent.value, "workflow": workflow.workflow_type}
                )
                yield await format_sse_event(start_event)
                
                complete_event = AgentTraceEvent(
                    event_type="complete",
                    message="Query processed (direct response)",
                    progress=100,
                    timestamp=get_utc_timestamp(),
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
            full_agent_response = None  # Store complete agent analysis result
            message_service = MessageService() if request.thread_id else None
            agent_trace_events = []  # Collect all trace events for persistence
            
            try:
                # Emit orchestration start event
                start_event = AgentTraceEvent(
                    event_type="orchestration_start",
                    message=f"Detected {intent.value} query, routing to {workflow.workflow_type}",
                    timestamp=get_utc_timestamp(),
                    data={
                        "intent": intent.value,
                        "workflow": workflow.workflow_type,
                        "agents": workflow.agents,
                        "timeout_seconds": timeout_seconds,
                        "endpoint": agent_endpoint
                    }
                )
                yield await format_sse_event(start_event)
                # Collect orchestration start event for trace persistence
                agent_trace_events.append({
                    "event_type": start_event.event_type,
                    "message": start_event.message,
                    "timestamp": start_event.timestamp,
                    "data": start_event.data,
                    "agent_name": None  # Orchestration events don't have agent_name
                })
                
                # Prepare agent request payload
                agent_payload = orchestrator.prepare_agent_request(
                    company_name=final_company_name,
                    trade_date=request.trade_date,
                    workflow=workflow,
                    conversation_context=request.conversation_context,
                    query=query_text  # Pass the extracted query for dynamic agent selection
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
                    # Use separate timeouts: short connect timeout, long read timeout for streaming
                    streaming_timeout = Timeout(
                        connect=60.0,  # 60 second connection timeout
                        read=None,     # No read timeout for streaming (let it run until completion)
                        write=30.0,    # 30 second write timeout
                        pool=10.0      # 10 second pool timeout
                    )
                    async with httpx.AsyncClient(timeout=streaming_timeout) as client:
                        async with client.stream("POST", agent_streaming_url, json=agent_request) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    # Parse the event to capture final response and collect for trace
                                    try:
                                        event_data = json.loads(line[6:])  # Remove "data: " prefix
                                        
                                        # Collect event for trace persistence
                                        agent_trace_events.append(event_data)
                                        
                                        # Capture final response from complete events
                                        if event_data.get("event_type") in ["complete", "analysis_complete"]:
                                            if event_data.get("data") and isinstance(event_data["data"], dict):
                                                data = event_data["data"]
                                                
                                                # Store the complete agent response for metadata
                                                full_agent_response = data
                                                
                                                # Extract full response text - prefer formatted response, then full analysis response
                                                # Check state for formatted_response first (query-aware formatted response)
                                                state_data = data.get("state", {})
                                                final_response_text = (
                                                    state_data.get("formatted_response") or  # Prefer formatted response (query-aware)
                                                    data.get("response") or  # Full analysis response
                                                    data.get("trader_investment_plan") or  # Trader's full plan
                                                    data.get("investment_plan") or  # Investment plan
                                                    data.get("judge_decision") or  # Judge decision
                                                    data.get("decision") or  # Just the decision
                                                    event_data.get("message", "")  # Fallback to message
                                                )
                                                
                                                # If we only got the decision, try to build a more complete response
                                                if final_response_text and final_response_text in ["BUY", "SELL", "HOLD"]:
                                                    # Build a comprehensive response from available data
                                                    reports = data.get("reports", {})
                                                    response_parts = []
                                                    
                                                    if reports.get("market"):
                                                        response_parts.append(f"**Market Analysis:**\n{reports['market'][:500]}...")
                                                    if reports.get("fundamentals"):
                                                        response_parts.append(f"**Fundamentals:**\n{reports['fundamentals'][:500]}...")
                                                    
                                                    if response_parts:
                                                        final_response_text = "\n\n".join(response_parts) + f"\n\n**Final Decision: {final_response_text}**"
                                                    else:
                                                        # At minimum, provide a meaningful response
                                                        final_response_text = f"Based on comprehensive analysis, the recommended action is: **{final_response_text}**"
                                                
                                                logger.info(f"Extracted final response (length: {len(final_response_text) if final_response_text else 0})")
                                    except (json.JSONDecodeError, KeyError) as e:
                                        logger.debug(f"Could not parse event data: {e}")
                                        pass  # Continue streaming even if parsing fails
                                    
                                    yield line + "\n"
                                elif line.strip() and not line.startswith(":"):
                                    # Handle any other SSE format lines
                                    yield line + "\n"
                    
                    # Generate PDF from the agent analysis (even without thread_id)
                            pdf_filename = None
                    if full_agent_response and final_response_text:
                                try:
                                    company = full_agent_response.get("company") or final_company_name or "UNKNOWN"
                                    date = full_agent_response.get("date") or request.trade_date
                                    decision = full_agent_response.get("decision", "UNKNOWN")
                                    # Use the inner state if present; fallback to full response to avoid empty PDFs
                                    state = full_agent_response.get("state") or full_agent_response
                                    
                                    pdf_buffer = generate_analysis_pdf(
                                        company=company,
                                        date=date,
                                        decision=decision,
                                        state=state
                                    )
                                    
                                    pdf_dir = "/app/data/pdfs"
                                    os.makedirs(pdf_dir, exist_ok=True)
                                    
                                    pdf_filename = f"Meridian_{company}_{date}.pdf"
                                    pdf_path = os.path.join(pdf_dir, pdf_filename)
                                    
                                    with open(pdf_path, 'wb') as f:
                                        f.write(pdf_buffer.read())
                                    
                                    logger.info(f"Generated PDF: {pdf_path}")
                                except Exception as pdf_error:
                                    logger.error(f"Failed to generate PDF: {pdf_error}", exc_info=True)
                            # Don't fail the request if PDF generation fails
                            
                    # Save agent response to database if thread_id is provided
                    if request.thread_id and final_response_text and message_service:
                        try:
                            metadata = {
                                "agent_trace": {
                                    "events": agent_trace_events,
                                    "agents_called": list(set(
                                        evt.get("agent_name") 
                                        for evt in agent_trace_events 
                                        if evt.get("agent_name")
                                    )),
                                    "intent": intent.value,
                                    "workflow": workflow.workflow_type
                                },
                                "source": "agent_service",
                                "workflow_type": workflow.workflow_type,
                                "agents_used": workflow.agents,
                                # Include full agent analysis for frontend breakdown
                                "agent_analysis": full_agent_response if full_agent_response else None,
                                # Include PDF filename for download (if generated)
                                "pdf_filename": pdf_filename
                            }
                            
                            assistant_msg = await message_service.save_assistant_message(
                                thread_id=request.thread_id,
                                content=final_response_text,
                                metadata=metadata
                            )
                            logger.info(
                                f"Saved agent response with trace to thread {request.thread_id}: "
                                f"{assistant_msg['message_id']} ({len(agent_trace_events)} trace events)"
                            )
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
                        timestamp=get_utc_timestamp()
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
                        timestamp=get_utc_timestamp(),
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
                        timestamp=get_utc_timestamp()
                    )
                    yield await format_sse_event(error_event)
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_event = AgentTraceEvent(
                    event_type="error",
                    message=f"Streaming failed: {str(e)}",
                    timestamp=get_utc_timestamp()
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
