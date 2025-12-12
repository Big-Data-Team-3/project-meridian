# meridian-agents/server.py - Agents Service API
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.openapi.utils import get_openapi
import json
import asyncio
from graph.trading_graph import TradingAgentsGraph
from graph.planner.models import ExecutionPlan
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
        FocusedAnalysisRequest,
        SelectiveAnalysisRequest
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
        FocusedAnalysisRequest,
        SelectiveAnalysisRequest
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


def clean_state_for_response(state: Dict[str, Any], execution_plan: Optional[ExecutionPlan] = None) -> Dict[str, Any]:
    """
    Clean state dictionary for response by removing empty fields and unused phases.
    
    Args:
        state: Raw state dictionary from graph execution
        execution_plan: Optional execution plan to determine which phases were used
    
    Returns:
        Cleaned state dictionary with only relevant fields
    """
    # Determine which phases were used from execution plan or state content
    include_debate = False
    include_risk = False
    
    if execution_plan:
        include_debate = any(agent_id in ["bull_researcher", "bear_researcher", "research_manager"] 
                            for agent_id in execution_plan.agents)
        include_risk = any(agent_id in ["risky_debator", "safe_debator", "neutral_debator", "risk_manager"]
                          for agent_id in execution_plan.agents)
    else:
        # Fallback: check state content
        include_debate = "investment_debate_state" in state and state.get("investment_debate_state")
        include_risk = "risk_debate_state" in state and state.get("risk_debate_state")
    
    cleaned = {}
    
    # Include reports (only if they have content)
    report_fields = [
        "market_report",
        "fundamentals_report", 
        "sentiment_report",
        "news_report",
        "information_report",
        "investment_plan",
        "trader_investment_plan",
        "final_trade_decision"
    ]
    
    for field in report_fields:
        if field in state and isinstance(state[field], str) and state[field].strip():
            cleaned[field] = state[field]
    
    # Only include debate state if debate phase was used and has content
    if include_debate and "investment_debate_state" in state:
        debate_state = state["investment_debate_state"]
        has_content = any([
            debate_state.get("bull_history", "").strip(),
            debate_state.get("bear_history", "").strip(),
            debate_state.get("judge_decision", "").strip()
        ])
        if has_content:
            cleaned["investment_debate_state"] = {
                "bull_history": debate_state.get("bull_history", ""),
                "bear_history": debate_state.get("bear_history", ""),
                "judge_decision": debate_state.get("judge_decision", "")
            }
    
    # Only include risk state if risk phase was used and has content
    if include_risk and "risk_debate_state" in state:
        risk_state = state["risk_debate_state"]
        has_content = any([
            risk_state.get("risky_history", "").strip(),
            risk_state.get("safe_history", "").strip(),
            risk_state.get("neutral_history", "").strip(),
            risk_state.get("judge_decision", "").strip()
        ])
        if has_content:
            cleaned["risk_debate_state"] = {
                "risky_history": risk_state.get("risky_history", ""),
                "safe_history": risk_state.get("safe_history", ""),
                "neutral_history": risk_state.get("neutral_history", ""),
                "judge_decision": risk_state.get("judge_decision", "")
            }
    
    return cleaned


def get_graph() -> TradingAgentsGraph:
    """
    Get or initialize TradingAgentsGraph instance (thread-safe).
    
    The graph is always dynamically constructed based on queries.
    No static/legacy graphs are used.
    
    Returns:
        TradingAgentsGraph instance
    
    Raises:
        GraphInitializationError: If graph initialization fails
    """
    global _graph_instance, _graph_initializing, _graph_init_error
    
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
            logger.info("Initializing TradingAgentsGraph (dynamic mode only)...")
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
    event_emitter: EventEmitter,
    query: Optional[str] = None,
    context: Optional[List[Dict[str, Any]]] = None
) -> tuple[Dict[str, Any], str]:
    """
    Run analysis with streaming events.
    
    Args:
        graph: TradingAgentsGraph instance
        company_name: Company name or ticker
        trade_date: Trade date
        event_emitter: EventEmitter for streaming events
        query: Optional query string for dynamic graph planning
        context: Optional conversation context
        
    Returns:
        Tuple of (final_state, decision)
    """
    # Enable streaming on graph
    graph.enable_event_streaming(event_emitter)
    
    # Run analysis (events will be emitted during execution)
    final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
        company_name.strip().upper(),
        trade_date,
        query=query,
        context=context
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
        
        # Extract query: Priority 1) Direct query parameter, 2) conversation_context, 3) default
        query = None
        
        # Priority 1: Use direct query parameter if provided
        if request_data.query:
            query = request_data.query.strip()
            logger.info(
                f"✅ Using direct query parameter: '{query[:200]}...'",
                extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
            )
        
        # Priority 2: Extract from conversation context (last user message)
        if not query and request_data.conversation_context:
            logger.info(
                f"Conversation context provided: {len(request_data.conversation_context)} messages",
                extra={"extra_fields": {"request_id": request_id, "context_count": len(request_data.conversation_context)}}
            )
            # Get last user message as the query
            user_messages = [msg for msg in request_data.conversation_context if msg.role == "user"]
            logger.info(
                f"Found {len(user_messages)} user messages in context",
                extra={"extra_fields": {"request_id": request_id, "user_message_count": len(user_messages)}}
            )
            if user_messages:
                query = user_messages[-1].content.strip()
                logger.info(
                    f"✅ Extracted query from context: '{query[:200]}...'",
                    extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
                )
        
        # Priority 3: Generate default query if still none
        if not query:
            query = f"Analyze {request_data.company_name} for trading decision as of {request_data.trade_date}"
            logger.warning(
                f"⚠️ Using default query (no user query found): '{query}'",
                extra={"extra_fields": {"request_id": request_id}}
            )
        
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
        final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date,
            query=query,  # Pass the extracted/generated query
            context=context_messages
        )
        
        response_time = time.time() - start_time
        
        # Clean state for response (remove empty fields and unused phases)
        # Extract execution plan from aggregated context (it's stored as dict)
        execution_plan_dict = aggregated_context.execution_plan if aggregated_context else None
        execution_plan_obj = None
        if execution_plan_dict:
            from graph.planner.models import ExecutionPlan
            try:
                execution_plan_obj = ExecutionPlan(**execution_plan_dict)
            except:
                execution_plan_obj = None
        
        cleaned_state = clean_state_for_response(
            final_state,
            execution_plan=execution_plan_obj
        )
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=cleaned_state
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
        
        # Get graph (always uses dynamic graph construction)
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
                # Extract query: Priority 1) Direct query parameter, 2) conversation_context, 3) default
                query = None
                
                # Priority 1: Use direct query parameter if provided
                if request_data.query:
                    query = request_data.query.strip()
                    logger.info(
                        f"✅ Using direct query parameter: '{query[:200]}...'",
                        extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
                    )
                
                # Priority 2: Extract from conversation context (last user message)
                if not query and request_data.conversation_context:
                    logger.info(
                        f"Conversation context provided: {len(request_data.conversation_context)} messages",
                        extra={"extra_fields": {"request_id": request_id, "context_count": len(request_data.conversation_context)}}
                    )
                    # Get last user message as the query
                    user_messages = [msg for msg in request_data.conversation_context if msg.role == "user"]
                    logger.info(
                        f"Found {len(user_messages)} user messages in context",
                        extra={"extra_fields": {"request_id": request_id, "user_message_count": len(user_messages)}}
                    )
                    if user_messages:
                        query = user_messages[-1].content.strip()
                        logger.info(
                            f"✅ Extracted query from context: '{query[:200]}...'",
                            extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
                        )
                
                # Priority 3: Generate default query if still none
                if not query:
                    query = f"Analyze {request_data.company_name} for trading decision as of {request_data.trade_date}"
                    logger.warning(
                        f"⚠️ Using default query (no user query found): '{query}'",
                        extra={"extra_fields": {"request_id": request_id}}
                    )
                
                # Process conversation context if provided
                context_messages = None
                if request_data.conversation_context:
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
                
                # Start analysis in background
                analysis_task = asyncio.create_task(
                    _run_analysis_with_streaming(
                        graph,
                        request_data.company_name,
                        request_data.trade_date,
                        event_emitter,
                        query=query,  # Pass the extracted/generated query
                        context=context_messages
                    )
                )
                
                # Stream events while analysis runs
                final_state = None
                decision = None
                analysis_complete = False
                analysis_complete_event_data = None  # Store data from analysis_complete event
                
                while not analysis_complete:
                    try:
                        # Wait for event or timeout
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                        yield format_sse_event(event)
                        
                        # Check if analysis complete
                        if event.event_type == "analysis_complete":
                            analysis_complete = True
                            # Store the event data which already contains the full response
                            analysis_complete_event_data = event.data if hasattr(event, 'data') else None
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
                # Send complete event even when decision is None (for simple analysis queries)
                if final_state:
                    # Use data from analysis_complete event if available (it has the full response)
                    # Otherwise, extract from final_state
                    if analysis_complete_event_data and isinstance(analysis_complete_event_data, dict):
                        # Use the response and decision from the analysis_complete event
                        full_response = analysis_complete_event_data.get("response", "")
                        event_decision = analysis_complete_event_data.get("decision")
                        event_state = analysis_complete_event_data.get("state", {})
                        
                        # Extract key reports from event state or final_state
                        summary_data = {
                            "decision": event_decision if event_decision is not None else decision,  # Can be None for simple analysis queries
                            "company": request_data.company_name,
                            "date": request_data.trade_date,
                            "response": str(full_response) if full_response else "Analysis complete",  # Full analysis response from event
                            "reports": {
                                "market": event_state.get("market_report") or final_state.get("market_report", ""),
                                "fundamentals": event_state.get("fundamentals_report") or final_state.get("fundamentals_report", ""),
                                "sentiment": event_state.get("sentiment_report") or final_state.get("sentiment_report", ""),
                                "news": event_state.get("news_report") or final_state.get("news_report", ""),
                                "information": event_state.get("information_report") or final_state.get("information_report", "")
                            }
                        }
                    else:
                        # Fallback: extract from final_state if event data not available
                        full_response = (
                            final_state.get("trader_investment_plan") or
                            final_state.get("investment_plan") or
                            final_state.get("investment_debate_state", {}).get("judge_decision") or
                            final_state.get("risk_debate_state", {}).get("judge_decision") or
                            final_state.get("market_report") or  # For market analyst queries
                            final_state.get("fundamentals_report") or  # For fundamentals analyst queries
                            final_state.get("information_report") or  # For information analyst queries
                            final_state.get("news_report") or
                            final_state.get("sentiment_report") or
                            (decision if decision else None)  # Fallback to decision only if it exists
                        )
                        
                        # Extract key reports for summary
                        summary_data = {
                            "decision": decision,  # Can be None for simple analysis queries
                            "company": request_data.company_name,
                            "date": request_data.trade_date,
                            "response": str(full_response) if full_response else "Analysis complete",  # Full analysis response
                            "reports": {
                                "market": final_state.get("market_report", ""),
                                "fundamentals": final_state.get("fundamentals_report", ""),
                                "sentiment": final_state.get("sentiment_report", ""),
                                "news": final_state.get("news_report", ""),
                                "information": final_state.get("information_report", "")
                            }
                        }
                    
                    # Only include serialized state if needed (it's large and may contain non-serializable objects)
                    # The state will be serialized by format_sse_event if included
                    complete_event = AgentStreamEvent(
                        event_type="complete",
                        message=f"Analysis complete for {request_data.company_name}",
                        progress=100,
                        data=summary_data
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
        
        # Get graph (always uses dynamic graph construction)
        graph = get_graph()
        
        # Process conversation context if provided
        context_messages = None
        query = None  # Extract query from conversation context
        
        if request_data.conversation_context:
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
            
            # Extract query from conversation context (last user message)
            user_messages = [msg for msg in request_data.conversation_context if msg.role == "user"]
            if user_messages:
                query = user_messages[-1].content.strip()
                logger.info(
                    f"✅ Extracted query from context: '{query[:200]}...'",
                    extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
                )
        
        # If no query found, generate a default based on agent type
        if not query:
            query = f"Analyze {request_data.company_name} using {agent_type} analysis as of {request_data.trade_date}"
            logger.info(
                f"⚠️ Using default query: '{query}'",
                extra={"extra_fields": {"request_id": request_id}}
            )
        
        # Run analysis
        final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date,
            query=query,  # Pass the extracted query instead of None
            context=context_messages
        )
        
        response_time = time.time() - start_time
        
        # Clean state for response (remove empty fields and unused phases)
        # Extract execution plan from aggregated context (it's stored as dict)
        execution_plan_dict = aggregated_context.execution_plan if aggregated_context else None
        execution_plan_obj = None
        if execution_plan_dict:
            from graph.planner.models import ExecutionPlan
            try:
                execution_plan_obj = ExecutionPlan(**execution_plan_dict)
            except:
                execution_plan_obj = None
        
        cleaned_state = clean_state_for_response(
            final_state,
            execution_plan=execution_plan_obj
        )
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=cleaned_state
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
        
        # Get graph (always uses dynamic graph construction)
        graph = get_graph()
        
        # Process conversation context if provided
        context_messages = None
        query = None  # Extract query from conversation context
        
        if request_data.conversation_context:
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
            
            # Extract query from conversation context (last user message)
            user_messages = [msg for msg in request_data.conversation_context if msg.role == "user"]
            if user_messages:
                query = user_messages[-1].content.strip()
                logger.info(
                    f"✅ Extracted query from context: '{query[:200]}...'",
                    extra={"extra_fields": {"request_id": request_id, "query_preview": query[:200]}}
                )
        
        # If no query found, generate a default
        if not query:
            query = f"Analyze {request_data.company_name} using {', '.join(request_data.agents)} analysis as of {request_data.trade_date}"
            logger.info(
                f"⚠️ Using default query: '{query}'",
                extra={"extra_fields": {"request_id": request_id}}
            )
        
        # Run analysis
        final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date,
            query=query,  # Pass the extracted query instead of None
            context=context_messages
        )
        
        response_time = time.time() - start_time
        
        # Clean state for response (remove empty fields and unused phases)
        # Extract execution plan from aggregated context (it's stored as dict)
        execution_plan_dict = aggregated_context.execution_plan if aggregated_context else None
        execution_plan_obj = None
        if execution_plan_dict:
            from graph.planner.models import ExecutionPlan
            try:
                execution_plan_obj = ExecutionPlan(**execution_plan_dict)
            except:
                execution_plan_obj = None
        
        cleaned_state = clean_state_for_response(
            final_state,
            execution_plan=execution_plan_obj
        )
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=cleaned_state
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
        
        # Get graph (always uses dynamic graph construction)
        graph = get_graph()
        
        # Process conversation context if provided
        context_messages = None
        if request_data.conversation_context:
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
        
        # Run analysis
        final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date,
            query=None,
            context=context_messages
        )
        
        response_time = time.time() - start_time
        
        # Clean state for response (remove empty fields and unused phases)
        # Extract execution plan from aggregated context (it's stored as dict)
        execution_plan_dict = aggregated_context.execution_plan if aggregated_context else None
        execution_plan_obj = None
        if execution_plan_dict:
            from graph.planner.models import ExecutionPlan
            try:
                execution_plan_obj = ExecutionPlan(**execution_plan_dict)
            except:
                execution_plan_obj = None
        
        cleaned_state = clean_state_for_response(
            final_state,
            execution_plan=execution_plan_obj
        )
        
        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=cleaned_state
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


@app.post("/analyze/selective", response_model=AnalyzeResponse)
async def analyze_selective(request_data: SelectiveAnalysisRequest, request: Request):
    """
    Analyze a company using a selective set of agents.

    Args:
        request_data: Analysis request with company name, trade date, and selective agents

    Selective agents can include:
        - Analysts: "market", "information", "fundamentals"
        - Researchers: "bull_researcher", "bear_researcher", "research_manager"
        - Traders: "trader"
        - Risk analysts: "risky_analyst", "neutral_analyst", "safe_analyst", "risk_judge"

    Timeout: Dynamic based on number of agents (15s per agent, min 60s).
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", f"req-{int(time.time() * 1000)}")

    try:
        # Input validation
        if not request_data.company_name or not request_data.company_name.strip():
            raise ValueError("company_name cannot be empty")

        if not request_data.trade_date:
            raise ValueError("trade_date is required")

        # Validate selective agents
        valid_agents = {
            "market", "information", "fundamentals",
            "bull_researcher", "bear_researcher", "research_manager",
            "trader",
            "risky_analyst", "neutral_analyst", "safe_analyst", "risk_judge"
        }

        invalid_agents = [agent for agent in request_data.selective_agents if agent not in valid_agents]
        if invalid_agents:
            raise ValueError(f"Invalid agents: {invalid_agents}. Valid agents: {sorted(valid_agents)}")

        logger.info(
            f"Selective analysis requested",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "endpoint": "/analyze/selective",
                    "company": request_data.company_name,
                    "selective_agents": request_data.selective_agents,
                    "include_debate": request_data.include_debate,
                    "include_risk": request_data.include_risk
                }
            }
        )

        # Create selective graph with only the requested agents
        # Filter to data-gathering agents only (market, information, fundamentals)
        data_agents = [agent for agent in request_data.selective_agents
                      if agent in ["market", "information", "fundamentals"]]

        if not data_agents:
            raise ValueError("At least one data-gathering agent (market, information, fundamentals) must be selected")

        # Get graph (always uses dynamic graph construction)
        graph = get_graph()

        # Process conversation context if provided
        context_messages = None
        if request_data.conversation_context:
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

        # Run selective analysis
        final_state, decision, aggregated_context, synthesizer_output = await graph.propagate(
            request_data.company_name.strip().upper(),
            request_data.trade_date,
            query=None,
            context=context_messages
        )

        response_time = time.time() - start_time

        # Clean state for response (remove empty fields and unused phases)
        # Extract execution plan from aggregated context (it's stored as dict)
        execution_plan_dict = aggregated_context.execution_plan if aggregated_context else None
        execution_plan_obj = None
        if execution_plan_dict:
            from graph.planner.models import ExecutionPlan
            try:
                execution_plan_obj = ExecutionPlan(**execution_plan_dict)
            except:
                execution_plan_obj = None
        
        cleaned_state = clean_state_for_response(
            final_state,
            execution_plan=execution_plan_obj
        )

        response = AnalyzeResponse(
            company=request_data.company_name,
            date=request_data.trade_date,
            decision=decision,
            state=cleaned_state
        )

        logger.info(
            f"Selective analysis completed",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "company": request_data.company_name,
                    "decision": decision,
                    "response_time": response_time,
                    "agents_used": len(request_data.selective_agents)
                }
            }
        )

        return response

    except Exception as e:
        logger.error(f"Selective analysis error: {e}", exc_info=True)
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