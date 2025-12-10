"""
Health check API endpoints.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    message: str | None = None
    service: str | None = None


@router.get("/", response_model=HealthResponse)
async def root():
    """Root health check endpoint"""
    return {
        "status": "ok",
        "message": "Meridian Backend API is running"
    }


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy"}


@router.get("/api/health", response_model=HealthResponse)
async def api_health():
    """API health check endpoint"""
    return {
        "status": "ok",
        "service": "meridian-backend"
    }

