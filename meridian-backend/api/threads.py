"""
Thread management API endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

from models.thread import (
    ThreadCreateRequest,
    ThreadResponse,
    ThreadListResponse,
    ThreadDeleteResponse
)
from services.thread_service import ThreadService
from api.error_handling import handle_api_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threads", tags=["threads"])

# Initialize thread service (lazy initialization to avoid startup errors)
_thread_service: Optional[ThreadService] = None


def get_thread_service() -> ThreadService:
    """Get or create thread service instance."""
    global _thread_service
    if _thread_service is None:
        _thread_service = ThreadService()
    return _thread_service


@router.post("", response_model=ThreadResponse, status_code=201)
async def create_thread(request: ThreadCreateRequest, http_request: Request):
    """
    Create a new conversation thread.
    
    Returns:
        ThreadResponse with thread_id, title, timestamps
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        thread = await service.create_thread(title=request.title)
        return ThreadResponse(**thread)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "create_thread", request_id=request_id)


@router.get("", response_model=ThreadListResponse)
async def list_threads(http_request: Request):
    """
    List all conversation threads, ordered by last activity (most recent first).
    
    Returns:
        ThreadListResponse with list of threads
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        threads = await service.list_threads()
        return ThreadListResponse(threads=threads)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "list_threads", request_id=request_id)


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str, http_request: Request):
    """
    Get a specific thread by ID.
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        ThreadResponse with thread data
    
    Raises:
        404: If thread not found
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        thread = await service.get_thread(thread_id)
        if not thread:
            raise HTTPException(
                status_code=404,
                detail=f"NOT_FOUND: Thread {thread_id} not found"
            )
        return ThreadResponse(**thread)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"get_thread({thread_id})", request_id=request_id)


@router.delete("/{thread_id}", response_model=ThreadDeleteResponse)
async def delete_thread(thread_id: str, http_request: Request):
    """
    Delete a thread and all its messages (cascade delete).
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        ThreadDeleteResponse with success status
    
    Raises:
        404: If thread not found
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        deleted = await service.delete_thread(thread_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"NOT_FOUND: Thread {thread_id} not found"
            )
        return ThreadDeleteResponse(success=True, thread_id=thread_id)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"delete_thread({thread_id})", request_id=request_id)

