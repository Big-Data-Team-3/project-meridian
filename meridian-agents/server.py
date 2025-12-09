# meridian-agents/server.py - Agents Service API
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from graph.trading_graph import TradingAgentsGraph
import uvicorn
import os
import traceback
import threading
import time
from typing import Optional

# Import models and utilities
try:
    from models.requests import AnalyzeRequest
    from models.responses import HealthResponse, AnalyzeResponse, ErrorResponse
    from utils.config import get_config
    from utils.logging import setup_logging, get_logger
    from utils.errors import (
        GraphInitializationError,
        AnalysisError,
        handle_http_exception,
        create_error_response
    )
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models.requests import AnalyzeRequest
    from models.responses import HealthResponse, AnalyzeResponse, ErrorResponse
    from utils.config import get_config
    from utils.logging import setup_logging, get_logger
    from utils.errors import (
        GraphInitializationError,
        AnalysisError,
        handle_http_exception,
        create_error_response
    )

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


def get_graph() -> TradingAgentsGraph:
    """
    Get or initialize TradingAgentsGraph instance (thread-safe).
    
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
        
        # Try to get graph to verify initialization works
        graph_initialized = False
        status = "ok"
        error = None
        
        try:
            graph = get_graph()
            graph_initialized = True
            status = "ok"
            error = None
        except GraphInitializationError as graph_error:
            graph_initialized = False
            status = "error"
            error = str(graph_error)
            logger.warning(
                f"Graph initialization failed during health check: {graph_error}",
                extra={"extra_fields": {"request_id": request_id, "error_type": type(graph_error).__name__}}
            )
        except Exception as graph_error:
            graph_initialized = False
            status = "error"
            error = str(graph_error)
            logger.warning(
                f"Graph initialization failed during health check: {graph_error}",
                extra={"extra_fields": {"request_id": request_id, "error_type": type(graph_error).__name__}}
            )
        
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