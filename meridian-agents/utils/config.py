"""
Environment configuration management for Meridian Agents Service.
Validates and provides access to environment variables.
"""
import os
from typing import Optional
from pathlib import Path


class Config:
    """Configuration manager for agents service."""
    
    # Required environment variables
    OPENAI_API_KEY: str
    PORT: int = 8001
    
    # Optional environment variables
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    LOG_FILE: Optional[Path] = None
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Required
        self.OPENAI_API_KEY = self._get_required("OPENAI_API_KEY")
        
        # Optional with defaults
        self.PORT = int(os.getenv("PORT", "8001"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
        
        # Log file path
        log_file_path = os.getenv("LOG_FILE")
        if log_file_path:
            self.LOG_FILE = Path(log_file_path)
        
        # Validate configuration
        self._validate()
    
    def _get_required(self, key: str) -> str:
        """
        Get required environment variable.
        
        Args:
            key: Environment variable name
        
        Returns:
            Environment variable value
        
        Raises:
            ValueError: If environment variable is not set
        """
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable {key} is not set"
            )
        return value
    
    def _validate(self) -> None:
        """Validate configuration values."""
        # Validate PORT
        if not (1 <= self.PORT <= 65535):
            raise ValueError(
                f"PORT must be between 1 and 65535, got {self.PORT}"
            )
        
        # Validate LOG_LEVEL
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in valid_log_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_log_levels}, got {self.LOG_LEVEL}"
            )
        
        # Validate ENVIRONMENT
        valid_environments = ["development", "production", "testing"]
        if self.ENVIRONMENT not in valid_environments:
            raise ValueError(
                f"ENVIRONMENT must be one of {valid_environments}, got {self.ENVIRONMENT}"
            )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.ENVIRONMENT == "testing"


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance.
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config

