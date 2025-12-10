"""
Thread management API endpoints.
All endpoints require authentication and are user-scoped.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends

from models.thread import (
    ThreadCreateRequest,
    ThreadResponse,
    ThreadListResponse,
    ThreadDeleteResponse
)
from services.thread_service import ThreadService
from api.error_handling import handle_api_error
from api.auth import require_auth

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
async def create_thread(
    request: ThreadCreateRequest,
    http_request: Request,
    current_user: dict = Depends(require_auth)
):
    """
    Create a new conversation thread for the authenticated user.
    
    Returns:
        ThreadResponse with thread_id, title, timestamps
    
    Raises:
        401: If not authenticated
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        thread = await service.create_thread(
            title=request.title,
            user_id=current_user["id"]
        )
        return ThreadResponse(**thread)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "create_thread", request_id=request_id)


@router.get("", response_model=ThreadListResponse)
async def list_threads(
    http_request: Request,
    current_user: dict = Depends(require_auth)
):
    """
    List all conversation threads for the authenticated user, 
    ordered by last activity (most recent first).
    
    Returns:
        ThreadListResponse with list of threads
    
    Raises:
        401: If not authenticated
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        logger.info(f"Listing threads for user: {current_user.get('id')}, email: {current_user.get('email')}")
        service = get_thread_service()
        threads = await service.list_threads(user_id=current_user["id"])
        logger.info(f"Found {len(threads)} threads for user {current_user.get('id')}")
        return ThreadListResponse(threads=threads)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_threads endpoint: {e}", exc_info=True)
        logger.error(f"User ID: {current_user.get('id') if current_user else 'None'}")
        raise handle_api_error(e, "list_threads", request_id=request_id)


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    http_request: Request,
    current_user: dict = Depends(require_auth)
):
    """
    Get a specific thread by ID for the authenticated user.
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        ThreadResponse with thread data
    
    Raises:
        401: If not authenticated
        404: If thread not found or not owned by user (to avoid information leakage)
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        thread = await service.get_thread(thread_id, user_id=current_user["id"])
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
async def delete_thread(
    thread_id: str,
    http_request: Request,
    current_user: dict = Depends(require_auth)
):
    """
    Delete a thread and all its messages (cascade delete) for the authenticated user.
    
    Args:
        thread_id: Thread identifier
    
    Returns:
        ThreadDeleteResponse with success status
    
    Raises:
        401: If not authenticated
        404: If thread not found or not owned by user (to avoid information leakage)
    """
    request_id = getattr(http_request.state, "request_id", None)
    try:
        service = get_thread_service()
        deleted = await service.delete_thread(thread_id, user_id=current_user["id"])
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

