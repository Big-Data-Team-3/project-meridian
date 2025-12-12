"""
Query intent classification service using LLM with Instructor structured outputs.
Classifies user queries to determine appropriate agent workflows.
"""

import logging
import os
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from models.query_intent import QueryIntent

logger = logging.getLogger(__name__)

try:
    import instructor
    from pydantic import BaseModel, Field
    import openai
    INSTRUCTOR_AVAILABLE = True

    class QueryClassification(BaseModel):
        """Structured classification response from LLM."""

        intent: QueryIntent = Field(description="The primary intent of the query")
        confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
        reasoning: str = Field(description="Brief explanation of classification")
        entities: List[str] = Field(description="Key entities (companies, tickers)", default_factory=list)
        requires_agents: bool = Field(description="Whether this needs agent workflows")
        complexity: str = Field(description="simple|medium|complex query complexity")

except (ImportError, PermissionError) as e:
    INSTRUCTOR_AVAILABLE = False
    logger.error(f"Instructor library not available: {e}. LLM classification requires instructor.")
    raise RuntimeError(f"LLM classification requires instructor library. Install with: pip install instructor")


class QueryClassifier:
    """Classifies user queries using LLM with Instructor structured outputs."""

    def __init__(self):
        """Initialize classifier."""
        if not INSTRUCTOR_AVAILABLE:
            raise RuntimeError("Instructor library is required for LLM classification")

        # Load environment variables from .env file
        load_dotenv()

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")

        # Initialize OpenAI with Instructor
        self.client = instructor.patch(openai.OpenAI(api_key=openai_api_key))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.classification_cache = {}
        logger.info(f"LLM classifier initialized with model: {self.model}")
    
    def classify(self, query: str, conversation_context: Optional[List[dict]] = None) -> QueryIntent:
        """
        Classify a user query using LLM with structured outputs.
        
        Args:
            query: User query text
            conversation_context: Optional conversation history for context
            
        Returns:
            QueryIntent enum value

        Raises:
            RuntimeError: If classification fails
        """
        if not query or not query.strip():
            return QueryIntent.SIMPLE_CHAT
        
        try:
            result = self._classify_with_llm(query, conversation_context)
            if result:
                logger.debug(f"LLM classified '{query[:50]}...' as {result.intent.value} (confidence: {result.confidence})")
                return result.intent
            else:
                raise RuntimeError("LLM classification returned no result")
        except Exception as e:
            logger.error(f"LLM classification failed for query '{query[:50]}...': {e}")
            raise RuntimeError(f"Query classification failed: {e}")
    
    def classify_with_entities(
        self, 
        query: str, 
        conversation_context: Optional[List[dict]] = None
    ) -> Optional[QueryClassification]:
        """
        Classify a user query and return full classification including entities.
        
        Args:
            query: User query text
            conversation_context: Optional conversation history for context
            
        Returns:
            QueryClassification object with intent, entities, and other metadata, or None if classification fails
        """
        if not query or not query.strip():
            return None
        
        try:
            result = self._classify_with_llm(query, conversation_context)
            if result:
                logger.debug(
                    f"LLM classified '{query[:50]}...' as {result.intent.value} "
                    f"(confidence: {result.confidence}, entities: {result.entities})"
                )
            return result
        except Exception as e:
            logger.error(f"LLM classification with entities failed for query '{query[:50]}...': {e}")
            return None

    def _classify_with_llm(self, query: str, context: Optional[List[dict]] = None) -> Optional[QueryClassification]:
        """Classify using LLM with structured output."""

        # Check cache first
        cache_key = f"{query}_{hash(str(context)) if context else ''}"
        if cache_key in self.classification_cache:
            return self.classification_cache[cache_key]

        # Build system prompt
        system_prompt = self._build_classification_prompt()

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation context if available
        if context:
            context_str = self._format_context(context)
            messages.append({"role": "system", "content": f"Conversation context:\n{context_str}"})

        # Add current query
        messages.append({"role": "user", "content": query})

        try:
            # Get structured classification
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=QueryClassification,
                max_retries=2,
                temperature=0.1  # Low temperature for consistent classification
            )

            # Cache result
            self.classification_cache[cache_key] = response

            return response

        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return None
    
    def _build_classification_prompt(self) -> str:
        """Build system prompt with examples and instructions."""
        return """
        You are an expert financial query classifier for Meridian, a multi-agent financial intelligence platform.

        Your task is to classify user queries into the most appropriate intent category.

        AVAILABLE INTENTS:

        SIMPLE_CHAT: Casual conversation, greetings, non-financial questions, questions about the AI itself
        Examples: "Hello", "How are you?", "What's your name?", "Tell me a joke", "Tell me about yourself", "Who are you?", "What is Meridian?", "What can you help me with?"

        BASIC_INFO: Company/ticker information lookup, business descriptions
        Examples: "What does Apple do?", "Tell me about Tesla", "What is NVIDIA's business?"

        TECHNICAL_ANALYSIS: Charts, indicators, technical patterns, price analysis
        Examples: "Show me AAPL charts", "Technical analysis of TSLA", "Moving averages for MSFT"

        FUNDAMENTAL_ANALYSIS: Financial statements, ratios, earnings, valuation
        Examples: "Apple's P/E ratio", "Tesla earnings report", "Microsoft balance sheet"

        NEWS_SENTIMENT: Recent news, market sentiment, social media analysis
        Examples: "Apple news today", "Market sentiment", "Tesla social media buzz"

        COMPREHENSIVE_TRADE: Investment decisions, buy/sell recommendations requiring full analysis
        Examples: "Should I buy Apple stock?", "Is Tesla undervalued?", "Investment thesis for NVIDIA"

        PORTFOLIO_REVIEW: Portfolio analysis, performance reviews, asset allocation
        Examples: "How is my portfolio doing?", "Review my investments", "Portfolio optimization"

        MARKET_OVERVIEW: Market-wide analysis, indices, broad market trends
        Examples: "Market summary today", "How did the Dow perform?", "Global market trends"

        IMPORTANT CONTEXT:
        - You are "Meridian", an AI financial assistant. Questions about "Meridian" refer to you, the AI, NOT a company.
        - Questions like "What is Meridian?", "Tell me about yourself", or "Who are you?" are SIMPLE_CHAT.

        CLASSIFICATION GUIDELINES:
        1. Consider the PRIMARY intent - what is the user really asking for?
        2. Look for financial vs casual context
        3. Consider complexity - does this require real-time data or agent workflows?
        4. Be specific - "Apple stock" alone might be BASIC_INFO, but "Should I buy Apple stock?" is COMPREHENSIVE_TRADE
        5. Use conversation context when available to understand follow-up questions
        6. Questions about the AI itself (you/Meridian) are always SIMPLE_CHAT, never requiring agent workflows

        ENTITY EXTRACTION:
        - Extract ALL company names and ticker symbols mentioned in the query
        - Include both company names (e.g., "Apple", "Tesla", "Microsoft") AND ticker symbols (e.g., "AAPL", "TSLA", "MSFT")
        - For company names, also include their ticker symbol if you know it (e.g., "Apple" -> include "AAPL" in entities)
        - Extract entities from conversation context if relevant
        - Examples:
          * "Should I buy Apple?" -> entities: ["Apple", "AAPL"]
          * "Tell me about TSLA" -> entities: ["TSLA", "Tesla"]
          * "What's the P/E ratio for Microsoft?" -> entities: ["Microsoft", "MSFT"]
          * "Compare Apple and Tesla" -> entities: ["Apple", "AAPL", "Tesla", "TSLA"]

        Output a JSON object with your classification, confidence score, brief reasoning, and extracted entities.
        """

    def _format_context(self, context: List[dict]) -> str:
        """Format conversation context for the prompt."""
        formatted = []
        for msg in context[-3:]:  # Last 3 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)



# Singleton instance
_query_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    """Get or create query classifier singleton."""
    global _query_classifier
    if _query_classifier is None:
        _query_classifier = QueryClassifier()
    return _query_classifier

