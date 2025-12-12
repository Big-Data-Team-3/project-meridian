"""
Planner Configuration

Configuration settings for the LLM Planner Agent.
"""

from typing import Dict, Any, Optional


class PlannerConfig:
    """
    Configuration for the LLM Planner Agent.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout_seconds: int = 30,
        enable_caching: bool = True,
        max_context_messages: int = 20,
        fallback_enabled: bool = True
    ):
        """
        Initialize planner configuration.
        
        Args:
            model: LLM model to use for planning (default: gpt-4o for better reasoning)
            temperature: Temperature for LLM (lower = more deterministic)
            max_tokens: Maximum tokens for planner response
            timeout_seconds: Timeout for planner LLM call
            enable_caching: Whether to cache planning results
            max_context_messages: Maximum conversation context messages to include
            fallback_enabled: Whether to use fallback planning if planner fails
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.enable_caching = enable_caching
        self.max_context_messages = max_context_messages
        self.fallback_enabled = fallback_enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "enable_caching": self.enable_caching,
            "max_context_messages": self.max_context_messages,
            "fallback_enabled": self.fallback_enabled
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PlannerConfig":
        """Create config from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def default(cls) -> "PlannerConfig":
        """Get default configuration."""
        return cls()


# Default configuration instance
DEFAULT_CONFIG = PlannerConfig.default()

