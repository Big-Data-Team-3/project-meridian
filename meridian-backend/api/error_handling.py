"""
Error handling utilities for API endpoints.
Provides consistent error response format and error detection.
"""
import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def is_database_error(error: Exception) -> bool:
    """
    Check if an error is a database-related error.
    
    Args:
        error: Exception to check
    
    Returns:
        True if error is database-related
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Check for common database error patterns
    db_keywords = [
        'database', 'connection', 'sql', 'postgres', 'pg8000',
        'connection pool', 'timeout', 'connection refused',
        'could not connect', 'operational error', 'interface error'
    ]
    
    return any(keyword in error_str or keyword in error_type for keyword in db_keywords)


def is_external_service_error(error: Exception) -> bool:
    """
    Check if an error is from an external service (OpenAI, Agents, etc.).
    
    Args:
        error: Exception to check
    
    Returns:
        True if error is from external service
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Check for external service error patterns
    external_keywords = [
        'openai', 'api error', 'rate limit', 'service unavailable',
        'agents service', 'httpx', 'request error', 'timeout'
    ]
    
    return any(keyword in error_str or keyword in error_type for keyword in external_keywords)


def handle_api_error(
    error: Exception,
    operation: str,
    default_status: int = 500,
    request_id: Optional[str] = None
) -> HTTPException:
    """
    Handle API errors with appropriate status codes and logging.
    
    Args:
        error: Exception that occurred
        operation: Description of the operation that failed
        default_status: Default HTTP status code
        request_id: Optional request ID for logging
    
    Returns:
        HTTPException with appropriate status code and error details
    """
    error_msg = str(error)
    error_type = type(error).__name__
    
    # Determine status code based on error type
    if is_database_error(error):
        status_code = 503
        error_code = "DATABASE_ERROR"
        error_detail = "Database service unavailable"
    elif is_external_service_error(error):
        status_code = 502
        error_code = "EXTERNAL_SERVICE_ERROR"
        error_detail = "External service error"
    elif "not found" in error_msg.lower():
        status_code = 404
        error_code = "NOT_FOUND"
        error_detail = error_msg
    elif "validation" in error_msg.lower() or "invalid" in error_msg.lower():
        status_code = 400
        error_code = "VALIDATION_ERROR"
        error_detail = error_msg
    else:
        status_code = default_status
        error_code = "INTERNAL_ERROR"
        error_detail = "An internal error occurred"
    
    # Log error with context
    log_context = {
        "operation": operation,
        "error_type": error_type,
        "error_code": error_code,
        "status_code": status_code
    }
    if request_id:
        log_context["request_id"] = request_id
    
    logger.error(
        f"API error in {operation}: {error_msg}",
        extra=log_context,
        exc_info=True
    )
    
    # Return HTTPException with error details
    # Note: FastAPI's HTTPException uses 'detail' field
    # For constitution compliance, we include error code in detail
    return HTTPException(
        status_code=status_code,
        detail=f"{error_code}: {error_detail}"
    )

