"""
Final Synthesizer Module

Provides the Final Synthesizer LLM that merges agent signals into coherent final answers.
"""

from .synthesizer import FinalSynthesizer
from .models import SynthesizerOutput
from .config import SynthesizerConfig, DEFAULT_CONFIG

__all__ = [
    "FinalSynthesizer",
    "SynthesizerOutput",
    "SynthesizerConfig",
    "DEFAULT_CONFIG",
]

