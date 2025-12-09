"""
Error handling utilities for Meridian Agents Service.
Provides custom exceptions and error response formatting.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException
import traceback
from .config import get_config


class AgentsServiceError(Exception):
    """Base exception for agents service errors."""
    pass


class GraphInitializationError(AgentsServiceError):
    """Raised when graph initialization fails."""
    pass


class AnalysisError(AgentsServiceError):
    """Raised when analysis fails."""
    pass


class ValidationError(AgentsServiceError):
    """Raised when request validation fails."""
    pass


def create_error_response(
    error: Exception,
    status_code: int = 500,
    include_traceback: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        error: Exception instance
        status_code: HTTP status code
        include_traceback: Whether to include traceback (default: based on environment)
    
    Returns:
        Error response dictionary
    """
    config = get_config()
    
    # Determine if traceback should be included
    if include_traceback is None:
        include_traceback = config.is_development
    
    response = {
        "detail": str(error),
        "error_type": type(error).__name__
    }
    
    # Add traceback in development mode
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response


def sanitize_error_for_production(error: Exception) -> str:
    """
    Sanitize error message for production.
    
    Args:
        error: Exception instance
    
    Returns:
        Sanitized error message
    """
    error_msg = str(error)
    
    # Remove sensitive information
    sensitive_patterns = [
        "api_key", "apiKey", "password", "token",
        "secret", "credential", "authorization"
    ]
    
    for pattern in sensitive_patterns:
        if pattern.lower() in error_msg.lower():
            error_msg = "An internal error occurred"
            break
    
    return error_msg


def handle_http_exception(
    error: Exception,
    status_code: int = 500,
    default_message: str = "An internal error occurred"
) -> HTTPException:
    """
    Create HTTPException with proper error handling.
    
    Args:
        error: Exception instance
        status_code: HTTP status code
        default_message: Default message for production
    
    Returns:
        HTTPException instance
    """
    config = get_config()
    
    if config.is_production:
        # Sanitize error in production
        detail = sanitize_error_for_production(error)
    else:
        # Include full error details in development
        detail = f"{str(error)}\n{traceback.format_exc()}"
    
    return HTTPException(
        status_code=status_code,
        detail=detail
    )

