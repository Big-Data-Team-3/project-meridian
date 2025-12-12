"""
Final Synthesizer Models

Defines data models for synthesizer output.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SynthesizerOutput(BaseModel):
    """
    Output from the Final Synthesizer.
    
    The synthesizer merges all agent outputs into a coherent final answer.
    """
    
    recommendation: Optional[str] = Field(
        None, 
        description="Final recommendation (e.g., BUY, SELL, HOLD). None for news-only queries."
    )
    reasoning: str = Field(
        ..., 
        description="Detailed reasoning explaining the recommendation"
    )
    agent_references: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of agent contributions referenced in the answer. Format: [{'agent_id': 'market_analyst', 'contribution': 'Technical analysis showed...'}]"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence level in the recommendation (0.0 to 1.0)"
    )
    
    # Optional fields
    summary: Optional[str] = Field(
        None,
        description="Brief summary of the analysis"
    )
    key_factors: Optional[List[str]] = Field(
        None,
        description="Key factors that influenced the decision"
    )
    risks: Optional[List[str]] = Field(
        None,
        description="Key risks identified"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "recommendation": "BUY",
                "reasoning": "Based on comprehensive analysis from multiple agents...",
                "agent_references": [
                    {"agent_id": "market_analyst", "contribution": "Technical indicators show bullish momentum"},
                    {"agent_id": "fundamentals_analyst", "contribution": "Strong financial health with growing revenue"}
                ],
                "confidence": 0.75,
                "summary": "Strong buy recommendation based on technical and fundamental analysis",
                "key_factors": ["Bullish technical indicators", "Strong fundamentals", "Positive sentiment"],
                "risks": ["Market volatility", "Regulatory concerns"]
            }
        }

