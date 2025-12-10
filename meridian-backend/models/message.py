"""
Pydantic models for message requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MessageResponse(BaseModel):
    """Response model for a single message."""
    message_id: str = Field(..., description="Unique message identifier")
    thread_id: str = Field(..., description="Thread identifier this message belongs to")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")


class MessageListResponse(BaseModel):
    """Response model for message list."""
    thread_id: str = Field(..., description="Thread identifier")
    messages: List[MessageResponse] = Field(..., description="List of messages in chronological order")

