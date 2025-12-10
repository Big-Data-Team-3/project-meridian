"""
Chat API endpoints.
All endpoints require authentication and are user-scoped via thread ownership.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from models.chat import ChatRequest, ChatResponse
from services.chat_service import ChatService
from api.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Initialize chat service (lazy initialization)
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create chat service instance."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(require_auth)
):
    """
    Send a chat message to a thread and receive an assistant response.
    Only processes messages for threads owned by the authenticated user.
    
    This endpoint:
    1. Verifies thread ownership
    2. Saves the user message to the database
    3. Retrieves conversation context (last N messages)
    4. Calls OpenAI API with the conversation context
    5. Saves the assistant response to the database
    6. Updates the thread's updated_at timestamp
    
    Args:
        request: ChatRequest with thread_id and message
    
    Returns:
        ChatResponse with message IDs and assistant response
    
    Raises:
        401: If not authenticated
        404: If thread not found or not owned by user (to avoid information leakage)
        502: If OpenAI API error
        503: If database error
    """
    try:
        service = get_chat_service()
        result = await service.process_chat_message(
            thread_id=request.thread_id,
            user_message=request.message,
            user_id=current_user["id"]
        )
        return ChatResponse(**result)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat endpoint error: {error_msg}", exc_info=True)
        
        # Determine status code based on error type
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=error_msg
            )
        elif "OpenAI" in error_msg or "openai" in error_msg:
            raise HTTPException(
                status_code=502,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=error_msg
            )

