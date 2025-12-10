"""
Query intent classification models.
Defines the different types of user queries and their characteristics.
"""
from enum import Enum


class QueryIntent(str, Enum):
    """Enumeration of possible query intents."""
    
    SIMPLE_CHAT = "simple_chat"
    """Casual conversation, no agents required. Examples: 'Hello', 'How are you?'"""
    
    BASIC_INFO = "basic_info"
    """Company/ticker information lookup. Examples: 'What is Apple?', 'Tell me about TSLA'"""
    
    TECHNICAL_ANALYSIS = "technical_analysis"
    """Chart/technical indicators analysis. Examples: 'AAPL charts', 'moving averages for MSFT'"""
    
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    """Financial metrics/ratios analysis. Examples: 'Apple earnings', 'P/E ratio for Tesla'"""
    
    NEWS_SENTIMENT = "news_sentiment"
    """News and sentiment analysis. Examples: 'Apple news', 'market sentiment today'"""
    
    COMPREHENSIVE_TRADE = "comprehensive_trade"
    """Investment decision queries requiring full agent workflow. Examples: 'Should I buy Apple?', 'Is Tesla a good investment?'"""
    
    PORTFOLIO_REVIEW = "portfolio_review"
    """Portfolio analysis. Examples: 'Review my portfolio', 'How is my portfolio performing?'"""
    
    MARKET_OVERVIEW = "market_overview"
    """Market-wide analysis. Examples: 'Market summary today', 'What moved markets?'"""

