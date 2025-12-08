"""
Barebones backend server for Meridian project.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Meridian Backend API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Meridian Backend API is running"}


@app.get("/health")
async def health():
    """Health check endpoint for Docker healthcheck."""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health():
    """API health check endpoint."""
    return {"status": "ok", "service": "meridian-backend"}

@app.get("/api/agents/health")
async def agents_health():
    """
    Agents health check endpoint.
    Returns status for agent backend.
    Uses AGENTS_SERVICE_URL environment variable (default: http://localhost:8001)
    For Docker, set AGENTS_SERVICE_URL=http://meridian-agents:8001
    """
    import httpx
    
    # Get agents service URL from environment, default to localhost for local dev
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

