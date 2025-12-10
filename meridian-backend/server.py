"""
Meridian Backend API Server
FastAPI application with modular API structure.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
import traceback

# Import API routers
from api import health
from api import threads
from api import messages
from api import chat
from api import auth
from api import agents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("meridian_backend")

# Create FastAPI app
app = FastAPI(title="Meridian Backend API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware for logging correlation
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracking."""
    import time
    request_id = f"req-{int(time.time() * 1000)}"
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(
            f"Request {request_id} failed: {e}",
            exc_info=True
        )
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception in request {request_id}: {exc}",
        exc_info=True
    )
    
    # Determine if we should include traceback
    try:
        from utils.config import get_config
        config = get_config()
        include_traceback = config.is_development
    except:
        include_traceback = True  # Default to True if config unavailable
    
    error_response = {
        "error": str(exc),
        "detail": str(exc),
        "request_id": request_id
    }
    
    if include_traceback:
        error_response["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=500,
        content=error_response
)

# Include API routers
app.include_router(health.router)
app.include_router(threads.router)
app.include_router(messages.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(agents.router)

# Server startup
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
