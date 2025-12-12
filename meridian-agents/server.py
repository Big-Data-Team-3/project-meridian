# meridian-agents/server.py - Agents Service API
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.openapi.utils import get_openapi
import json
import asyncio
from graph.trading_graph import TradingAgentsGraph
import uvicorn
import os
import traceback
import threading
import time
from typing import Optional, List, Dict, Any

# Import models and utilities
try:
    from models.requests import (
        AnalyzeRequest,
        SingleAgentRequest,
        MultiAgentRequest,
        FocusedAnalysisRequest
    )
    from models.responses import HealthResponse, AnalyzeResponse, ErrorResponse
    from utils.config import get_config
    from utils.logging import setup_logging, get_logger
    from utils.errors import (
        GraphInitializationError,
        AnalysisError,
        handle_http_exception,
        create_error_response
    )
    try:
        from utils.streaming import EventEmitter, AgentStreamEvent
        from utils.sse_formatter import format_sse_event
        STREAMING_AVAILABLE = True
    except ImportError:
        STREAMING_AVAILABLE = False
        EventEmitter = None
        AgentStreamEvent = None
        format_sse_event = None
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models.requests import (
        AnalyzeRequest,
        SingleAgentRequest,
        MultiAgentRequest,
        FocusedAnalysisRequest
    )
    from models.responses import HealthResponse, AnalyzeResponse, ErrorResponse
    from utils.config import get_config
    from utils.logging import setup_logging, get_logger
    from utils.errors import (
        GraphInitializationError,
        AnalysisError,
        handle_http_exception,
        create_error_response
    )
    try:
        from utils.streaming import EventEmitter, AgentStreamEvent
        from utils.sse_formatter import format_sse_event
        STREAMING_AVAILABLE = True
    except ImportError:
        STREAMING_AVAILABLE = False
        EventEmitter = None
        AgentStreamEvent = None
        format_sse_event = None

# Initialize configuration and logging
try:
    config = get_config()
    logger = setup_logging(
        log_level=config.LOG_LEVEL,
        log_file=config.LOG_FILE,
        enable_json=True
    )
except Exception as e:
    # Fallback logging if config fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("meridian_agents")
    logger.warning(f"Failed to load configuration: {e}")

app = FastAPI(
    title="Meridian Agents API",
    description="Financial analysis agents service using OpenAI Agents SDK and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Meridian Agents API",
        version="1.0.0",
        description="""
        Financial analysis agents service that orchestrates multiple specialized agents
        to provide comprehensive trading decisions.
        
        **Features**:
        - Multi-agent financial analysis
        - Conversation context support
        - Thread-safe graph initialization
        - Structured JSON logging
        """,
        routes=app.routes,
    )
    
    # Add examples to schema
    openapi_schema["components"]["schemas"]["AnalyzeRequest"]["example"] = {
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
    
    openapi_schema["components"]["schemas"]["HealthResponse"]["example"] = {
        "status": "ok",
        "service": "meridian-agents",
        "graph_initialized": True
    }
    
    openapi_schema["components"]["schemas"]["AnalyzeResponse"]["example"] = {
        "company": "AAPL",
        "date": "2024-12-19",
        "decision": "BUY",
        "state": {
            "market_report": "Market analysis...",
            "fundamentals_report": "Fundamental analysis...",
            "information_report": "News and sentiment analysis..."
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracking."""
    import time
    request_id = f"req-{int(time.time() * 1000)}"
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        return response
    finally:
        # Cleanup if needed
        pass

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread-safe graph initialization
_graph_instance: Optional[TradingAgentsGraph] = None
_graph_lock = threading.Lock()
_graph_initializing = False
_graph_init_error: Optional[Exception] = None

# Cache for graphs with specific agent selections
_graph_cache: Dict[str, TradingAgentsGraph] = {}
_graph_cache_lock = threading.Lock()


def get_graph(selected_analysts: Optional[List[str]] = None) -> TradingAgentsGraph:
    """
    Get or initialize TradingAgentsGraph instance (thread-safe).
    
    Args:
        selected_analysts: Optional list of analyst types. If None, uses default.
                          If provided, returns a graph with only those analysts.
    
    Returns:
        TradingAgentsGraph instance
    
    Raises:
        GraphInitializationError: If graph initialization fails
    """
    global _graph_instance, _graph_initializing, _graph_init_error, _graph_cache
    
    # If specific analysts requested, use cache
    if selected_analysts is not None:
        # Sort to ensure consistent cache key
        cache_key = ",".join(sorted(selected_analysts))
        
        with _graph_cache_lock:
            if cache_key in _graph_cache:
                return _graph_cache[cache_key]
            
            # Create new graph with specific analysts
            try:
                logger.info(f"Creating graph with analysts: {selected_analysts}")
                graph = TradingAgentsGraph(selected_analysts=selected_analysts)
                _graph_cache[cache_key] = graph
                return graph
            except Exception as e:
                logger.error(f"Failed to create graph with analysts {selected_analysts}: {e}", exc_info=True)
                raise GraphInitializationError(f"Failed to create graph: {e}") from e
    
    # Default graph (all analysts)
    # Double-check locking pattern
    if _graph_instance is not None:
        return _graph_instance
    
    with _graph_lock:
        # Check again after acquiring lock
        if _graph_instance is not None:
            return _graph_instance
        
        # Check if initialization is in progress
        if _graph_initializing:
            # Wait for initialization to complete
            while _graph_initializing:
                time.sleep(0.1)
            if _graph_instance is not None:
                return _graph_instance
            if _graph_init_error:
                raise GraphInitializationError(
                    f"Graph initialization failed: {_graph_init_error}"
                ) from _graph_init_error
        
        # Start initialization
        _graph_initializing = True
        _graph_init_error = None
        
        try:
            logger.info("Initializing TradingAgentsGraph...")
            _graph_instance = TradingAgentsGraph()
            logger.info("TradingAgentsGraph initialized successfully")
            return _graph_instance
        except Exception as e:
            _graph_init_error = e
            logger.error(
                f"Failed to initialize TradingAgentsGraph: {e}",
                exc_info=True
            )
            raise GraphInitializationError(
                f"Failed to initialize TradingAgentsGraph: {e}"
            ) from e
        finally:
            _graph_initializing = False

@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """
    Health check endpoint.
    Returns service status and graph initialization state.
    Always returns HTTP 200, even if graph initialization fails.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    try:
        logger.info(
            f"Health check requested",
            extra={"extra_fields": {"request_id": request_id, "endpoint": "/health", "method": "GET"}}
        )
        
        # Check graph initialization status (non-blocking, quick check)
        graph_initialized = False
        status = "ok"
        error = None
        
        # Quick check: if graph is already initialized, we're good
        if _graph_instance is not None:
            graph_initialized = True
            status = "ok"
        elif _graph_initializing:
            # Graph is initializing, service is starting up
            graph_initialized = False
            status = "starting"
            error = "Graph initialization in progress"
        elif _graph_init_error:
            # Graph initialization previously failed
            graph_initialized = False
            status = "error"
            error = str(_graph_init_error)
        else:
            # Graph not initialized yet, but service is ready
            # Don't trigger initialization here - let it happen on first request
            graph_initialized = False
            status = "ok"
            error = None
        
        response_time = time.time() - start_time
        
        # Validate response time (< 5 seconds per constitution)
        if response_time > 5.0:
            logger.warning(
                f"Health check response time exceeded 5 seconds: {response_time:.2f}s",
                extra={"request_id": request_id, "response_time": response_time}
            )
        
        response = HealthResponse(
            status=status,
            service="meridian-agents",
            graph_initialized=graph_initialized,
            error=error
        )
        
        logger.info(
            f"Health check completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "status": status,
                    "graph_initialized": graph_initialized,
                    "response_time": response_time
                }
            }
        )
        
        return response
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(
            f"Unexpected error in health check: {e}",
            extra={"extra_fields": {"request_id": request_id, "error_type": type(e).__name__}},
            exc_info=True
        )
        
        # Always return HTTP 200 with error details
        return HealthResponse(
            status="error",
            service="meridian-agents",
            graph_initialized=False,
            error=str(e)
        )

async def _run_analysis_with_streaming(
    graph: TradingAgentsGraph,
    company_name: str,
    trade_date: str,
    event_emitter: EventEmitter
) -> tuple[Dict[str, Any], str]:
    """
    Run analysis with streaming events.
    
    Args:
        graph: TradingAgentsGraph instance
        company_name: Company name or ticker
        trade_date: Trade date
        event_emitter: EventEmitter for streaming events
        
    Returns:
        Tuple of (final_state, decision)
    """
    # Enable streaming on graph
    graph.enable_event_streaming(event_emitter)
    
    # Run analysis (events will be emitted during execution)
    final_state, decision = await graph.propagate(
        company_name.strip().upper(),
        trade_date
    )
    
    return final_state, decision


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request_data: AnalyzeRequest, request: Request):
    """
    Analyze a company using the agents service.
    Accepts company name, trade date, and optional conversation context.
    
    Timeout: 300 seconds (5 minutes) for long-running analyses.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    try:
        # Input validation (additional to Pydantic validation)
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")
        
        if not request_data.trade_date:
            raise ValueError("trade_date is required")
        
        # Validate date format
        try:
            from datetime import datetime
            datetime.strptime(request_data.trade_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid trade_date format: {request_data.trade_date}. Expected YYYY-MM-DD")
        
        # Log with request ID in extra fields (not as LogRecord attribute)
        log_extra = {
            "request_id": request_id,
            "endpoint": "/analyze",
            "company": request_data.company_name,
            "trade_date": request_data.trade_date,
            "has_context": request_data.conversation_context is not None,
            "context_count": len(request_data.conversation_context) if request_data.conversation_context else 0
        }
        logger.info(f"Analysis requested", extra=log_extra)
        
        # Get graph (will initialize if needed)
        graph = get_graph()
        
        # Process conversation context if provided
        context_messages = None
        if request_data.conversation_context:
            # Limit context to last 20 messages (constitution requirement)
            MAX_CONTEXT_MESSAGES = 20
            context_list = request_data.conversation_context[-MAX_CONTEXT_MESSAGES:]
            
            context_messages = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in context_list
            ]
            if context_messages:
                logger.debug(
                    f"Processing {len(context_messages)} context messages (limited from {len(request_data.conversation_context)})",
                    extra={"extra_fields": {"request_id": request_id, "context_count": len(context_messages)}}
                )
        
        # Run analysis (timeout handled by uvicorn/async framework)
        final_state, decision = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date
        )
        
        response_time = time.time() - start_time
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=final_state
        )
        
        logger.info(
            f"Analysis completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "company": request_data.company_name,
                    "decision": decision,
                    "response_time": response_time
                }
            }
        )
        
        return response
        
    except GraphInitializationError as e:
        response_time = time.time() - start_time
        logger.error(
            f"Graph initialization error during analysis: {e}",
            extra={"extra_fields": {"request_id": request_id, "error_type": type(e).__name__}},
            exc_info=True
        )
        raise handle_http_exception(e, status_code=500)
        
    except AnalysisError as e:
        response_time = time.time() - start_time
        logger.error(
            f"Analysis error: {e}",
            extra={"extra_fields": {"request_id": request_id, "error_type": type(e).__name__}},
            exc_info=True
        )
        raise handle_http_exception(e, status_code=500)
        
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(
            f"Unexpected error during analysis: {e}",
            extra={"extra_fields": {"request_id": request_id, "error_type": type(e).__name__}},
            exc_info=True
        )
        raise handle_http_exception(e, status_code=500)


@app.post("/analyze/stream")
async def analyze_stream(request_data: AnalyzeRequest, request: Request):
    """
    Stream agent analysis in real-time using Server-Sent Events.
    
    This endpoint streams progress updates as SSE events during agent execution.
    Returns both streaming events and final result.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    if not STREAMING_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Streaming not available - streaming utilities not found"
        )
    
    try:
        # Input validation
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")
        
        logger.info(
            f"Streaming analysis requested",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "endpoint": "/analyze/stream",
                    "company": request_data.company_name
                }
            }
        )
        
        # Get graph
        graph = get_graph()
        
        # Create event emitter and queue for events
        event_emitter = EventEmitter()
        event_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        
        def event_callback(event: AgentStreamEvent):
            """Callback to queue events for SSE streaming."""
            # Use call_soon_threadsafe to safely add to queue from any thread
            try:
                loop.call_soon_threadsafe(event_queue.put_nowait, event)
            except RuntimeError:
                # If loop is closed or not running, create new task
                try:
                    asyncio.create_task(event_queue.put(event))
                except:
                    pass  # Ignore if we can't queue the event
        
        event_emitter.on(event_callback)
        
        async def event_generator():
            """Generate SSE events from agent execution."""
            try:
                # Start analysis in background
                analysis_task = asyncio.create_task(
                    _run_analysis_with_streaming(
                        graph,
                        request_data.company_name,
                        request_data.trade_date,
                        event_emitter
                    )
                )
                
                # Stream events while analysis runs
                final_state = None
                decision = None
                analysis_complete = False
                
                while not analysis_complete:
                    try:
                        # Wait for event or timeout
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                        yield format_sse_event(event)
                        
                        # Check if analysis complete
                        if event.event_type == "analysis_complete":
                            analysis_complete = True
                            # Get final result from task
                            final_state, decision = await analysis_task
                            
                    except asyncio.TimeoutError:
                        # Check if analysis task is done
                        if analysis_task.done():
                            analysis_complete = True
                            try:
                                final_state, decision = analysis_task.result()
                            except Exception as e:
                                error_event = AgentStreamEvent(
                                    event_type="error",
                                    message=f"Analysis failed: {str(e)}"
                                )
                                yield format_sse_event(error_event)
                                return
                        # Continue waiting for events
                        continue
                
                # Send final result as completion event if not already sent
                if final_state and decision:
                    # Extract full response text from state (not just decision)
                    # Prefer trader_investment_plan as it contains the complete analysis
                    full_response = (
                        final_state.get("trader_investment_plan") or
                        final_state.get("investment_plan") or
                        final_state.get("investment_debate_state", {}).get("judge_decision") or
                        final_state.get("risk_debate_state", {}).get("judge_decision") or
                        decision  # Fallback to decision if nothing else available
                    )
                    
                    # Prepare serializable state using graph's method
                    serializable_state = graph._prepare_serializable_state(final_state)
                    
                    # Complete data with FULL state breakdown
                    complete_data = {
                        "decision": decision,
                        "company": request_data.company_name,
                        "date": request_data.trade_date,
                        "state": serializable_state,  # ← FULL STATE for frontend breakdown
                        "response": str(full_response),  # Full analysis response text
                    }
                    
                    # Only include serialized state if needed (it's large and may contain non-serializable objects)
                    # The state will be serialized by format_sse_event if included
                    complete_event = AgentStreamEvent(
                        event_type="complete",
                        message=f"Analysis complete for {request_data.company_name}",
                        progress=100,
                        data=complete_data
                    )
                    yield format_sse_event(complete_event)
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_event = AgentStreamEvent(
                    event_type="error",
                    message=f"Streaming failed: {str(e)}"
                )
                yield format_sse_event(error_event)
        
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
        logger.error(f"Streaming analysis error: {e}", exc_info=True)
        raise handle_http_exception(e, status_code=500)


@app.post("/analyze/single/{agent_type}", response_model=AnalyzeResponse)
async def analyze_single_agent(agent_type: str, request_data: SingleAgentRequest, request: Request):
    """
    Analyze a company using a single specific agent.
    
    Args:
        agent_type: Type of agent to use ('market', 'fundamentals', or 'information')
        request_data: Analysis request with company name and trade date
    
    Timeout: 60 seconds for single-agent analysis.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    # Validate agent type
    valid_agents = ["market", "fundamentals", "information"]
    if agent_type not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_type: {agent_type}. Must be one of: {valid_agents}"
        )
    
    try:
        # Input validation
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")
        
        logger.info(
            f"Single-agent analysis requested",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "endpoint": f"/analyze/single/{agent_type}",
                    "company": request_data.company_name,
                    "agent_type": agent_type
                }
            }
        )
        
        # Get graph with only the specified agent
        graph = get_graph(selected_analysts=[agent_type])
        
        # Process conversation context if provided
        if request_data.conversation_context:
            MAX_CONTEXT_MESSAGES = 20
            context_list = request_data.conversation_context[-MAX_CONTEXT_MESSAGES:]
        
        # Run analysis
        final_state, decision = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date
        )
        
        response_time = time.time() - start_time
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=final_state
        )
        
        logger.info(
            f"Single-agent analysis completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "agent_type": agent_type,
                    "decision": decision,
                    "response_time": response_time
                }
            }
        )
        
        return response
        
    except GraphInitializationError as e:
        raise handle_http_exception(e, status_code=500)
    except Exception as e:
        logger.error(f"Single-agent analysis error: {e}", exc_info=True)
        raise handle_http_exception(e, status_code=500)


@app.post("/analyze/multi", response_model=AnalyzeResponse)
async def analyze_multi_agent(request_data: MultiAgentRequest, request: Request):
    """
    Analyze a company using multiple selected agents.
    
    Args:
        request_data: Analysis request with company name, trade date, and agent list
    
    Timeout: 120 seconds for multi-agent analysis.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    try:
        # Validate agents
        valid_agents = ["market", "fundamentals", "information"]
        for agent in request_data.agents:
            if agent not in valid_agents:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid agent: {agent}. Must be one of: {valid_agents}"
                )
        
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")
        
        logger.info(
            f"Multi-agent analysis requested",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "endpoint": "/analyze/multi",
                    "company": request_data.company_name,
                    "agents": request_data.agents,
                    "include_debate": request_data.include_debate,
                    "include_risk": request_data.include_risk
                }
            }
        )
        
        # Get graph with selected agents
        graph = get_graph(selected_analysts=request_data.agents)
        
        # Process conversation context if provided
        if request_data.conversation_context:
            MAX_CONTEXT_MESSAGES = 20
            context_list = request_data.conversation_context[-MAX_CONTEXT_MESSAGES:]
        
        # Run analysis
        final_state, decision = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date
        )
        
        response_time = time.time() - start_time
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=final_state
        )
        
        logger.info(
            f"Multi-agent analysis completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "agents": request_data.agents,
                    "decision": decision,
                    "response_time": response_time
                }
            }
        )
        
        return response
        
    except GraphInitializationError as e:
        raise handle_http_exception(e, status_code=500)
    except Exception as e:
        logger.error(f"Multi-agent analysis error: {e}", exc_info=True)
        raise handle_http_exception(e, status_code=500)


@app.post("/analyze/focused", response_model=AnalyzeResponse)
async def analyze_focused(request_data: FocusedAnalysisRequest, request: Request):
    """
    Analyze a company with a specific focus area.
    
    Args:
        request_data: Analysis request with company name, trade date, and focus area
    
    Focus options:
        - 'sentiment_only': Information analyst focused on sentiment
        - 'technical_only': Market analyst focused on technical analysis
        - 'fundamental_only': Fundamentals analyst focused on financials
    
    Timeout: 45 seconds for focused analysis.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")
    
    # Map focus to agent
    focus_to_agent = {
        "sentiment_only": "information",
        "technical_only": "market",
        "fundamental_only": "fundamentals"
    }
    
    if request_data.focus not in focus_to_agent:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid focus: {request_data.focus}. Must be one of: {list(focus_to_agent.keys())}"
        )
    
    try:
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")
        
        agent_type = focus_to_agent[request_data.focus]
        
        logger.info(
            f"Focused analysis requested",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "endpoint": "/analyze/focused",
                    "company": request_data.company_name,
                    "focus": request_data.focus,
                    "agent_type": agent_type
                }
            }
        )
        
        # Get graph with focused agent
        graph = get_graph(selected_analysts=[agent_type])
        
        # Process conversation context if provided
        if request_data.conversation_context:
            MAX_CONTEXT_MESSAGES = 20
            context_list = request_data.conversation_context[-MAX_CONTEXT_MESSAGES:]
        
        # Run analysis
        final_state, decision = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date
        )
        
        response_time = time.time() - start_time
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=final_state
        )
        
        logger.info(
            f"Focused analysis completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "focus": request_data.focus,
                    "decision": decision,
                    "response_time": response_time
                }
            }
        )
        
        return response
        
    except GraphInitializationError as e:
        raise handle_http_exception(e, status_code=500)
    except Exception as e:
        logger.error(f"Focused analysis error: {e}", exc_info=True)
        raise handle_http_exception(e, status_code=500)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": request_id, "error_type": type(exc).__name__},
        exc_info=True
    )
    
    try:
        current_config = get_config()
        include_traceback = current_config.is_development
    except:
        include_traceback = True  # Default to True if config unavailable
    
    error_response = create_error_response(exc, include_traceback=include_traceback)
    return JSONResponse(
        status_code=500,
        content=error_response
    )


if __name__ == "__main__":
    try:
        config = get_config()
        port = config.PORT
        logger.info(f"Starting Meridian Agents Service on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.critical(f"Failed to start service: {e}", exc_info=True)
        raise