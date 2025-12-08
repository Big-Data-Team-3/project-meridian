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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

