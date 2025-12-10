"""
Query intent classification service.
Classifies user queries to determine appropriate agent involvement.
"""
import re
import logging
from typing import Optional, List
from models.query_intent import QueryIntent

logger = logging.getLogger(__name__)


class QueryClassifier:
    """Service for classifying user query intents."""
    
    # Keywords and patterns for each intent
    SIMPLE_CHAT_KEYWORDS = [
        'hello', 'hi', 'hey', 'how are you', 'what\'s up', 'good morning',
        'good afternoon', 'good evening', 'thanks', 'thank you', 'bye',
        'joke', 'tell me a story', 'what time', 'weather'
    ]
    
    BASIC_INFO_KEYWORDS = [
        'what is', 'tell me about', 'explain', 'what does', 'who is',
        'company overview', 'business model', 'what company'
    ]
    
    TECHNICAL_KEYWORDS = [
        'chart', 'charts', 'technical', 'moving average', 'rsi', 'macd',
        'bollinger', 'support', 'resistance', 'trend', 'pattern',
        'price action', 'candlestick', 'indicator', 'momentum'
    ]
    
    FUNDAMENTAL_KEYWORDS = [
        'earnings', 'revenue', 'profit', 'p/e', 'pe ratio', 'p/b', 'pb ratio',
        'roe', 'roa', 'debt', 'balance sheet', 'cash flow', 'dividend',
        'valuation', 'financials', 'fundamentals', 'ratios', 'metrics'
    ]
    
    NEWS_SENTIMENT_KEYWORDS = [
        'news', 'headlines', 'sentiment', 'rumors', 'announcement',
        'press release', 'media', 'coverage', 'buzz', 'trending'
    ]
    
    COMPREHENSIVE_TRADE_KEYWORDS = [
        'should i buy', 'should i sell', 'investment', 'invest in',
        'good investment', 'bad investment', 'buy or sell', 'hold or sell',
        'trading decision', 'investment decision', 'recommendation',
        'analysis', 'comprehensive', 'full analysis', 'detailed analysis'
    ]
    
    PORTFOLIO_KEYWORDS = [
        'portfolio', 'my holdings', 'my stocks', 'my investments',
        'portfolio performance', 'review portfolio', 'portfolio analysis'
    ]
    
    MARKET_OVERVIEW_KEYWORDS = [
        'market', 'markets', 'market summary', 'market overview',
        'what moved', 'market today', 'market performance', 'sector',
        'indices', 'dow', 'sp500', 'nasdaq', 'market trends'
    ]
    
    # Ticker symbol pattern (2-5 uppercase letters)
    TICKER_PATTERN = re.compile(r'\b[A-Z]{2,5}\b')
    
    # Company name patterns
    COMPANY_NAME_PATTERNS = [
        r'\b(apple|microsoft|tesla|amazon|google|meta|nvidia|netflix)\b',
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(inc|corp|llc|ltd|company)\b'
    ]
    
    def classify(self, query: str, conversation_context: Optional[List[dict]] = None) -> QueryIntent:
        """
        Classify a user query to determine appropriate agent involvement.
        
        Args:
            query: User query text
            conversation_context: Optional conversation history for context
            
        Returns:
            QueryIntent enum value
        """
        if not query or not query.strip():
            return QueryIntent.SIMPLE_CHAT
        
        query_lower = query.lower().strip()
        
        # Check for simple chat first (highest priority to avoid false positives)
        if self._is_simple_chat(query_lower):
            logger.debug(f"Classified as SIMPLE_CHAT: {query[:50]}")
            return QueryIntent.SIMPLE_CHAT
        
        # Check for comprehensive trade decision (requires full workflow)
        if self._is_comprehensive_trade(query_lower):
            logger.debug(f"Classified as COMPREHENSIVE_TRADE: {query[:50]}")
            return QueryIntent.COMPREHENSIVE_TRADE
        
        # Check for portfolio review
        if self._is_portfolio_review(query_lower):
            logger.debug(f"Classified as PORTFOLIO_REVIEW: {query[:50]}")
            return QueryIntent.PORTFOLIO_REVIEW
        
        # Check for market overview
        if self._is_market_overview(query_lower):
            logger.debug(f"Classified as MARKET_OVERVIEW: {query[:50]}")
            return QueryIntent.MARKET_OVERVIEW
        
        # Check for technical analysis
        if self._is_technical_analysis(query_lower):
            logger.debug(f"Classified as TECHNICAL_ANALYSIS: {query[:50]}")
            return QueryIntent.TECHNICAL_ANALYSIS
        
        # Check for fundamental analysis
        if self._is_fundamental_analysis(query_lower):
            logger.debug(f"Classified as FUNDAMENTAL_ANALYSIS: {query[:50]}")
            return QueryIntent.FUNDAMENTAL_ANALYSIS
        
        # Check for news/sentiment
        if self._is_news_sentiment(query_lower):
            logger.debug(f"Classified as NEWS_SENTIMENT: {query[:50]}")
            return QueryIntent.NEWS_SENTIMENT
        
        # Check for basic info (fallback for company-related queries)
        if self._is_basic_info(query_lower):
            logger.debug(f"Classified as BASIC_INFO: {query[:50]}")
            return QueryIntent.BASIC_INFO
        
        # Default to basic info if query contains ticker or company name
        if self._contains_ticker_or_company(query_lower):
            logger.debug(f"Classified as BASIC_INFO (ticker/company detected): {query[:50]}")
            return QueryIntent.BASIC_INFO
        
        # Final fallback to simple chat
        logger.debug(f"Classified as SIMPLE_CHAT (fallback): {query[:50]}")
        return QueryIntent.SIMPLE_CHAT
    
    def _is_simple_chat(self, query: str) -> bool:
        """Check if query is simple casual conversation."""
        return any(keyword in query for keyword in self.SIMPLE_CHAT_KEYWORDS)
    
    def _is_basic_info(self, query: str) -> bool:
        """Check if query is basic information request."""
        return any(keyword in query for keyword in self.BASIC_INFO_KEYWORDS)
    
    def _is_technical_analysis(self, query: str) -> bool:
        """Check if query is technical analysis request."""
        return any(keyword in query for keyword in self.TECHNICAL_KEYWORDS)
    
    def _is_fundamental_analysis(self, query: str) -> bool:
        """Check if query is fundamental analysis request."""
        return any(keyword in query for keyword in self.FUNDAMENTAL_KEYWORDS)
    
    def _is_news_sentiment(self, query: str) -> bool:
        """Check if query is news/sentiment analysis request."""
        return any(keyword in query for keyword in self.NEWS_SENTIMENT_KEYWORDS)
    
    def _is_comprehensive_trade(self, query: str) -> bool:
        """Check if query requires comprehensive trade analysis."""
        return any(keyword in query for keyword in self.COMPREHENSIVE_TRADE_KEYWORDS)
    
    def _is_portfolio_review(self, query: str) -> bool:
        """Check if query is portfolio review request."""
        return any(keyword in query for keyword in self.PORTFOLIO_KEYWORDS)
    
    def _is_market_overview(self, query: str) -> bool:
        """Check if query is market overview request."""
        return any(keyword in query for keyword in self.MARKET_OVERVIEW_KEYWORDS)
    
    def _contains_ticker_or_company(self, query: str) -> bool:
        """Check if query contains ticker symbol or company name."""
        # Check for ticker symbols (2-5 uppercase letters)
        if self.TICKER_PATTERN.search(query):
            return True
        
        # Check for company name patterns
        for pattern in self.COMPANY_NAME_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        return False


# Singleton instance
_query_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    """Get or create query classifier singleton."""
    global _query_classifier
    if _query_classifier is None:
        _query_classifier = QueryClassifier()
    return _query_classifier

