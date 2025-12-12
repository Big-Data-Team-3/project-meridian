"""
Pydantic models for thread requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ThreadCreateRequest(BaseModel):
    """Request model for creating a new thread."""
    title: Optional[str] = Field(None, description="Optional thread title", max_length=500)


class ThreadResponse(BaseModel):
    """Response model for thread data."""
    thread_id: str = Field(..., description="Unique thread identifier")
    title: Optional[str] = Field(None, description="Thread title")
    created_at: str = Field(..., description="Thread creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Thread last update timestamp (ISO format)")
    user_id: Optional[str] = Field(None, description="User ID (for future multi-user support)")


class ThreadListResponse(BaseModel):
    """Response model for thread list."""
    threads: list[ThreadResponse] = Field(..., description="List of threads")


class ThreadDeleteResponse(BaseModel):
    """Response model for thread deletion."""
    success: bool = Field(..., description="Deletion success status")
    thread_id: str = Field(..., description="Deleted thread ID")

