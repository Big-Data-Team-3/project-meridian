"""
Synthesizer Configuration

Configuration settings for the Final Synthesizer LLM.
"""

from typing import Dict, Any, Optional


class SynthesizerConfig:
    """
    Configuration for the Final Synthesizer.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout_seconds: int = 60,
        enable_structured_output: bool = True
    ):
        """
        Initialize synthesizer configuration.
        
        Args:
            model: LLM model to use (default: gpt-4o for better synthesis)
            temperature: Temperature for LLM (lower = more deterministic)
            max_tokens: Maximum tokens for synthesizer response
            timeout_seconds: Timeout for synthesizer LLM call
            enable_structured_output: Whether to request structured JSON output
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.enable_structured_output = enable_structured_output
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
            "enable_structured_output": self.enable_structured_output
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SynthesizerConfig":
        """Create config from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def default(cls) -> "SynthesizerConfig":
        """Get default configuration."""
        return cls()


# Default configuration instance
DEFAULT_CONFIG = SynthesizerConfig.default()

