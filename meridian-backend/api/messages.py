"""
Message management API endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException

from models.message import MessageResponse, MessageListResponse
from services.message_service import MessageService
from services.thread_service import ThreadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads", tags=["messages"])

# Initialize services (lazy initialization)
_message_service: Optional[MessageService] = None
_thread_service: Optional[ThreadService] = None


def get_message_service() -> MessageService:
    """Get or create message service instance."""
    global _message_service
    if _message_service is None:
        _message_service = MessageService()
    return _message_service


def get_thread_service() -> ThreadService:
    """Get or create thread service instance."""
    global _thread_service
    if _thread_service is None:
        _thread_service = ThreadService()
    return _thread_service


@router.get("/{thread_id}/messages", response_model=MessageListResponse)
async def get_thread_messages(thread_id: str):
    """
    Get all messages for a thread, ordered chronologically.
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        MessageListResponse with list of messages
    
    Raises:
        404: If thread not found
    """
    try:
        # First verify thread exists
        thread_service = get_thread_service()
        thread = await thread_service.get_thread(thread_id)
        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"Thread {thread_id} not found"
            )
        
        # Get messages
        service = get_message_service()
        messages = await service.get_messages_by_thread(thread_id)
        
        return MessageListResponse(
            thread_id=thread_id,
            messages=[MessageResponse(**msg) for msg in messages]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get messages: {str(e)}"
        )

