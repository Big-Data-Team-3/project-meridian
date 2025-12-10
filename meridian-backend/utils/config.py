"""
Environment configuration management for Meridian Backend.
Validates and provides access to environment variables for database and OpenAI.
"""
import os
from typing import Optional
from pathlib import Path


class Config:
    """Configuration manager for backend service."""
    
    # Database configuration
    DB_HOST: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_TYPE: str = "postgresql"
    
    # OpenAI configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    
    # Application configuration
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    
    # Conversation settings
    MAX_CONVERSATION_HISTORY: int = 20
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Database (required)
        self.DB_HOST = self._get_required("DB_HOST")
        self.DB_USER = self._get_required("DB_USER")
        self.DB_PASSWORD = self._get_required("DB_PASSWORD")
        self.DB_NAME = self._get_required("DB_NAME")
        self.DB_TYPE = os.getenv("DB_TYPE", "postgresql").lower()
        
        # OpenAI (required)
        self.OPENAI_API_KEY = self._get_required("OPENAI_API_KEY")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # Application (optional with defaults)
        self.PORT = int(os.getenv("PORT", "8000"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
        
        # Conversation settings
        self.MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
        
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
                f"Required environment variable {key} is not set. "
                f"Please set it in your environment or .env file."
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
        
        # Validate DB_TYPE
        valid_db_types = ["postgresql", "mysql"]
        if self.DB_TYPE not in valid_db_types:
            raise ValueError(
                f"DB_TYPE must be one of {valid_db_types}, got {self.DB_TYPE}"
            )
        
        # Validate MAX_CONVERSATION_HISTORY
        if self.MAX_CONVERSATION_HISTORY < 1 or self.MAX_CONVERSATION_HISTORY > 100:
            raise ValueError(
                f"MAX_CONVERSATION_HISTORY must be between 1 and 100, got {self.MAX_CONVERSATION_HISTORY}"
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

