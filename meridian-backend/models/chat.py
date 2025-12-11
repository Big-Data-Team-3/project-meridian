"""
Pydantic models for chat requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """Request model for sending a chat message."""
    thread_id: str = Field(..., description="Thread identifier to send message to")
    message: str = Field(..., description="User message content", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "message": "What is the weather today?"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat message."""
    thread_id: str = Field(..., description="Thread identifier")
    message_id: str = Field(..., description="User message ID")
    assistant_message_id: Optional[str] = Field(None, description="Assistant response message ID (None if use_streaming=True)")
    response: Optional[str] = Field(None, description="Assistant response content (None if use_streaming=True)")
    use_streaming: bool = Field(False, description="Whether frontend should use streaming endpoint")
    intent: Optional[str] = Field(None, description="Query intent classification")
    workflow: Optional[str] = Field(None, description="Agent workflow type (if use_streaming=True)")
    agents: Optional[list] = Field(None, description="List of agents to be used (if use_streaming=True)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "thread-abc123",
                "message_id": "msg-user-123",
                "assistant_message_id": "msg-assistant-456",
                "response": "The weather today is sunny with a high of 75°F."
            }
        }

