"""
Structured logging infrastructure for Meridian Agents Service.
Provides JSON-formatted logging with request tracking and error context.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID and other fields from extra_fields dict
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_data.update(record.extra_fields)
        
        # Add error context if present
        if hasattr(record, "error_context"):
            log_data["error_context"] = record.error_context
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_json: bool = True
) -> logging.Logger:
    """
    Setup structured logging for the agents service.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        enable_json: Enable JSON formatting (default: True)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("meridian_agents")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    if enable_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "meridian_agents") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def sanitize_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data from log entries.
    
    Args:
        data: Dictionary potentially containing sensitive data
    
    Returns:
        Sanitized dictionary
    """
    sensitive_keys = [
        "api_key", "apiKey", "api_key", "password", "token",
        "secret", "credential", "authorization", "auth"
    ]
    
    sanitized = data.copy()
    for key in sensitive_keys:
        if key.lower() in str(sanitized).lower():
            # Replace with masked value
            for k in sanitized.keys():
                if key.lower() in k.lower():
                    sanitized[k] = "***REDACTED***"
    
    return sanitized

