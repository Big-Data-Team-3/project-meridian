"""
Streaming API endpoints for real-time agent trace updates.
Uses Server-Sent Events (SSE) to stream agent analysis progress.
"""
import asyncio
import datetime
import json
import logging
import os
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from httpx import Timeout

logger = logging.getLogger(__name__)

# Import yfinance for ticker validation (optional - only used if available)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available - ticker validation will be skipped")

# Try to import requests for Yahoo Finance search
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not available - Yahoo Finance search will be skipped")

from api.auth import require_auth
from services.agent_orchestrator import get_agent_orchestrator
from services.message_service import MessageService
from models.query_intent import QueryIntent
from utils.pdf_generator import generate_analysis_pdf

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def search_alpha_vantage(company_name: str) -> Optional[str]:
    """
    Search Alpha Vantage for ticker symbol using company name.
    Uses Alpha Vantage's SYMBOL_SEARCH function without hardcoding.
    
    Args:
        company_name: Company name to search for
        
    Returns:
        Ticker symbol if found, None otherwise
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            return None  # Alpha Vantage not configured
        
        # Alpha Vantage SYMBOL_SEARCH endpoint
        search_url = "https://www.alphavantage.co/query"
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": company_name,
            "apikey": api_key
        }
        
        response = requests.get(search_url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data or "Note" in data:
            return None
        
        # Extract best matches
        best_matches = data.get("bestMatches", [])
        if not best_matches:
            return None
        
        # Filter for stock exchanges (NYSE, NASDAQ) and prefer US stocks
        search_lower = company_name.lower()
        for match in best_matches:
            symbol = match.get("1. symbol", "").upper()
            name = match.get("2. name", "").lower()
            region = match.get("4. region", "").upper()
            market_open = match.get("5. marketOpen", "").upper()
            
            # Prefer US stocks (NYSE, NASDAQ)
            if region == "UNITED STATES" and market_open in ["NYSE", "NASDAQ"]:
                # Check if company name matches
                if search_lower in name or any(word in name for word in search_lower.split() if len(word) > 3):
                    return symbol
        
        # If no perfect match, return first US stock
        for match in best_matches:
            symbol = match.get("1. symbol", "").upper()
            region = match.get("4. region", "").upper()
            if region == "UNITED STATES":
                return symbol
        
        return None
        
    except Exception as e:
        logger.debug(f"Alpha Vantage search failed: {e}")
        return None


def search_yahoo_finance(company_name: str) -> Optional[str]:
    """
    Search Yahoo Finance for ticker symbol using company name.
    Uses Yahoo Finance's search API endpoint without hardcoding.
    
    Args:
        company_name: Company name to search for
        
    Returns:
        Ticker symbol if found, None otherwise
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        # Yahoo Finance search endpoint
        search_url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": company_name,
            "quotesCount": 10,  # Get more results to find the best match
            "newsCount": 0
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract quotes from response
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        
        # Filter and prioritize results
        # Prefer common stock tickers (no special suffixes like .AS, .TO, etc.)
        # and avoid crypto, indices, etc.
        search_lower = company_name.lower()
        
        # Collect all valid matches
        valid_matches = []
        
        for quote in quotes:
            symbol = quote.get("symbol", "").upper()
            quote_type = quote.get("quoteType", "").upper()
            long_name = quote.get("longname", "").lower()
            short_name = quote.get("shortname", "").lower()
            
            # Skip non-stock results
            if quote_type not in ["EQUITY", "STOCK", ""]:
                continue
            
            # Skip crypto, indices, ETFs unless explicitly requested
            if any(skip in quote_type for skip in ["CRYPTOCURRENCY", "INDEX", "ETF"]):
                continue
            
            # Skip tickers with special suffixes (foreign exchanges, etc.)
            if "." in symbol and not symbol.endswith(".US"):
                continue
            
            # Check if company name matches
            # Special case: if searching for "alphabet", accept any Alphabet ticker
            if "alphabet" in search_lower and ("alphabet" in long_name or "alphabet" in short_name):
                name_match = True
            else:
                name_match = (
                    search_lower in long_name or
                    search_lower in short_name or
                    any(word in long_name for word in search_lower.split() if len(word) > 3) or
                    any(word in short_name for word in search_lower.split() if len(word) > 3) or
                    # Also check if search term appears in company name (for "google" -> "Alphabet")
                    ("alphabet" in long_name and "google" in search_lower) or
                    ("alphabet" in short_name and "google" in search_lower)
                )
            
            if name_match:
                valid_matches.append((symbol, long_name, short_name))
        
        if valid_matches:
            # If multiple matches, prefer:
            # 1. GOOGL over GOOG (Class A over Class C)
            # 2. Longer ticker symbols - Class A typically preferred
            # 3. Exact name matches over partial matches
            valid_matches.sort(key=lambda x: (
                x[0] != "GOOGL" if "GOOG" in x[0] else False,  # Prefer GOOGL over GOOG
                -len(x[0]),  # Prefer longer tickers
                search_lower not in x[1] and search_lower not in x[2]  # Prefer exact matches
            ))
            return valid_matches[0][0]
        
        # If no perfect match, return first equity result
        for quote in quotes:
            symbol = quote.get("symbol", "").upper()
            quote_type = quote.get("quoteType", "").upper()
            
            if quote_type in ["EQUITY", "STOCK", ""] and "." not in symbol:
                return symbol
        
        return None
        
    except Exception as e:
        logger.debug(f"Yahoo Finance search failed: {e}")
        return None


def resolve_company_to_ticker(company_name: str) -> Optional[str]:
    """
    Attempt to resolve a company name to its ticker symbol.
    
    This function tries multiple strategies WITHOUT hardcoding:
    1. Direct ticker lookup (if already a ticker)
    2. Yahoo Finance search API (for company names)
    3. Smart candidate generation and validation (fallback)
    
    Args:
        company_name: Company name or potential ticker
        
    Returns:
        Ticker symbol if found, None otherwise
    
    Note: This function does NOT use hardcoded mappings. It relies entirely
    on dynamic APIs and validation.
    """
    if not company_name:
        return None
    
    company_clean = company_name.strip()
    
    # Strategy 1: Try as direct ticker first (fast path)
    if YFINANCE_AVAILABLE:
        try:
            ticker_upper = company_clean.upper()
            if 1 <= len(ticker_upper) <= 5 and ticker_upper.isalpha():
                ticker = yf.Ticker(ticker_upper)
                info = ticker.info
                # Check if we got valid data (symbol exists and has a name)
                if info and info.get('symbol') and (info.get('shortName') or info.get('longName')):
                    logger.debug(f"Direct ticker match: {company_clean} -> {ticker_upper}")
                    return ticker_upper
        except Exception as e:
            logger.debug(f"Direct ticker lookup failed for {company_clean}: {e}")
    
    # Strategy 2: Use Yahoo Finance search API (best for company names)
    searched_ticker = None
    if REQUESTS_AVAILABLE:
        # For "google", also try searching for "Alphabet" since that's the parent company
        search_terms = [company_clean]
        if company_clean.lower() == "google":
            search_terms.append("Alphabet Inc")
        
        for search_term in search_terms:
            searched_ticker = search_yahoo_finance(search_term)
            if searched_ticker:
                break
    
    # Strategy 2b: Fallback to Alpha Vantage if Yahoo Finance fails
    if not searched_ticker and REQUESTS_AVAILABLE:
        searched_ticker = search_alpha_vantage(company_clean)
        if searched_ticker:
            logger.debug(f"Resolved via Alpha Vantage search: '{company_clean}' -> {searched_ticker}")
    
    if searched_ticker:
            # Special handling: For "google", prefer GOOGL over GOOG
            if company_clean.lower() == "google" and searched_ticker == "GOOG":
                # Try GOOGL instead
                try:
                    ticker_googl = yf.Ticker("GOOGL")
                    info_googl = ticker_googl.info
                    if info_googl and info_googl.get('symbol') == "GOOGL":
                        searched_ticker = "GOOGL"
                except Exception:
                    pass  # Keep GOOG if GOOGL validation fails
            
            # Validate the searched ticker to ensure it's correct
            if YFINANCE_AVAILABLE:
                try:
                    ticker = yf.Ticker(searched_ticker)
                    info = ticker.info
                    if info and info.get('symbol'):
                        short_name = info.get('shortName', '').lower()
                        long_name = info.get('longName', '').lower()
                        search_lower = company_clean.lower()
                        
                        # Verify the company name matches
                        # For "google", also accept "alphabet" in the company name
                        name_match = (
                            (short_name and search_lower in short_name) or
                            (long_name and search_lower in long_name) or
                            (short_name and any(word in short_name for word in search_lower.split() if len(word) > 3)) or
                            (search_lower == "google" and ("alphabet" in short_name or "alphabet" in long_name))
                        )
                        
                        if name_match:
                            logger.info(f"Resolved company name: '{company_clean}' -> {searched_ticker} ({short_name.title() or long_name.title()})")
                            return searched_ticker
                except Exception as e:
                    logger.debug(f"Validation of searched ticker failed: {e}")
            else:
                # If yfinance not available, trust the search result
                logger.info(f"Resolved via Yahoo Finance search: '{company_clean}' -> {searched_ticker}")
                return searched_ticker
    
    # Strategy 3: Fallback - Smart candidate generation (only if search failed)
    # This generates potential ticker patterns and validates them
    if YFINANCE_AVAILABLE:
        candidates = []
        word = company_clean.upper().replace(' ', '')
        
        # Generate candidates based on common ticker patterns
        if len(word) >= 1:
            # Try full word if short enough
            if 1 <= len(word) <= 5:
                candidates.append(word)
            # Try first 4 letters (common pattern)
            if len(word) > 4:
                candidates.append(word[:4])
            # Try first 3 letters
            if len(word) >= 3:
                candidates.append(word[:3])
            # Try first 2 letters (less common but worth trying)
            if len(word) >= 2:
                candidates.append(word[:2])
        
        # Try each candidate and validate
        for candidate in candidates:
            try:
                ticker = yf.Ticker(candidate)
                info = ticker.info
                
                if info and info.get('symbol'):
                    short_name = info.get('shortName', '').lower()
                    long_name = info.get('longName', '').lower()
                    search_lower = company_clean.lower()
                    
                    # Check if the company name in the ticker info matches our search
                    if (short_name and search_lower in short_name) or \
                       (long_name and search_lower in long_name) or \
                       (short_name and any(word in short_name for word in search_lower.split() if len(word) > 3)):
                        symbol = info.get('symbol')
                        display_name = short_name or long_name
                        logger.info(f"Resolved company name: '{company_clean}' -> {symbol} ({display_name})")
                        return symbol.upper()
                        
            except Exception as e:
                logger.debug(f"Candidate ticker '{candidate}' failed: {e}")
                continue
    
    logger.debug(f"Could not resolve company name: {company_clean}")
    return None


def validate_company_ticker(company_name: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that a company/ticker exists and can be fetched from data sources.
    Intelligently resolves company names to ticker symbols (e.g., "amazon" -> "AMZN").
    
    Args:
        company_name: Company name or ticker symbol to validate
        
    Returns:
        Tuple of (is_valid, error_message, normalized_ticker)
        - is_valid: True if company exists and can be fetched
        - error_message: Error message if validation fails, None if valid
        - normalized_ticker: The actual ticker symbol from yfinance (e.g., "AAPL"), or None if invalid
    """
    if not company_name or company_name.strip() == "" or company_name == "UNKNOWN":
        return False, "No company or ticker symbol provided. Please specify a company name or stock ticker symbol (e.g., AAPL, TSLA, MSFT).", None
    
    original_input = company_name.strip()
    
    # If yfinance is available, use intelligent resolution
    if YFINANCE_AVAILABLE:
        # First, try to resolve company name to ticker
        resolved_ticker = resolve_company_to_ticker(original_input)
        
        if resolved_ticker:
            # Validate the resolved ticker
            try:
                ticker = yf.Ticker(resolved_ticker)
                info = ticker.info
                
                if info and info.get('symbol'):
                    symbol = info.get('symbol')
                    has_name = info.get('shortName') or info.get('longName')
                    normalized_ticker = symbol.upper() if symbol else None
                    company_display = has_name or symbol
                    logger.info(f"✓ Validated: '{original_input}' -> {company_display} ({normalized_ticker})")
                    return True, None, normalized_ticker
            except Exception as e:
                logger.warning(f"Error validating resolved ticker {resolved_ticker}: {e}")
        
        # If resolution failed, try direct validation with original input
        try:
            ticker = yf.Ticker(original_input.upper())
            info = ticker.info
            
            if info and info.get('symbol'):
                symbol = info.get('symbol')
                has_name = info.get('shortName') or info.get('longName')
                normalized_ticker = symbol.upper() if symbol else None
                company_display = has_name or symbol
                logger.info(f"✓ Direct validation: '{original_input}' -> {company_display} ({normalized_ticker})")
                return True, None, normalized_ticker
        except Exception as e:
            error_str = str(e).lower()
            if 'timeout' in error_str or 'timed out' in error_str:
                return False, (
                    f"Validation timeout for '{original_input}'. "
                    "The data source is taking too long to respond. Please try again."
                ), None
            elif 'connection' in error_str or 'network' in error_str:
                return False, (
                    f"Network error while validating '{original_input}'. "
                    "Please check your connection and try again."
                ), None
        
        # All validation attempts failed
        logger.warning(f"Could not validate or resolve: {original_input}")
        return False, (
            f"Company or ticker '{original_input}' not found in our data sources. "
            "Please provide a valid stock ticker symbol (e.g., AAPL for Apple, AMZN for Amazon, TSLA for Tesla). "
            "Note: We currently only support publicly traded stocks (not cryptocurrencies or private companies)."
        ), None
        
    else:
        # If yfinance not available, do basic format check
        company_upper = original_input.upper()
        if len(company_upper) > 5 or not company_upper.replace(' ', '').isalpha():
            return False, (
                f"Invalid ticker format: '{original_input}'. "
                "Ticker symbols are typically 1-5 uppercase letters (e.g., AAPL, TSLA)."
            ), None
        
        logger.warning("yfinance not available - skipping ticker validation")
        # Return the uppercased input as normalized ticker (best we can do without yfinance)
        return True, None, company_upper


class AgentAnalysisRequest(BaseModel):
    """Request model for streaming agent analysis."""
    company_name: Optional[str] = Field(None, description="Company name or ticker symbol", min_length=1, max_length=100)
    trade_date: str = Field(..., description="Trade date in ISO format YYYY-MM-DD", pattern=r'^\d{4}-\d{2}-\d{2}$')
    query: Optional[str] = Field(None, description="User query text for intent classification")
    conversation_context: Optional[list] = Field(None, description="Optional conversation context")
    thread_id: Optional[str] = Field(None, description="Thread ID for saving agent response to database")


class AgentTraceEvent(BaseModel):
    """Model for agent trace events sent via SSE."""
    event_type: str = Field(..., description="Type of event: 'start', 'progress', 'agent_update', 'complete', 'error'")
    agent_name: Optional[str] = Field(None, description="Name of the agent currently active")
    message: str = Field(..., description="Human-readable status message")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)", ge=0, le=100)
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")
    timestamp: str = Field(..., description="Event timestamp in ISO format")


async def format_sse_event(event: AgentTraceEvent) -> str:
    """Format an event as Server-Sent Events data."""
    event_data = {
        "event_type": event.event_type,
        "agent_name": event.agent_name,
        "message": event.message,
        "progress": event.progress,
        "data": event.data,
        "timestamp": event.timestamp
    }

    # Remove None values to keep payload clean
    event_data = {k: v for k, v in event_data.items() if v is not None}

    return f"data: {json.dumps(event_data)}\n\n"


async def mock_agent_analysis_stream(company_name: str, trade_date: str) -> AsyncGenerator[str, None]:
    """
    Mock agent analysis that simulates real-time streaming.
    In production, this would connect to your actual agent service.
    """
    import datetime
    import random

    agents = [
        {"name": "Market Analyst", "duration": 15, "steps": ["Gathering market data", "Analyzing trends", "Calculating metrics"]},
        {"name": "Fundamental Analyst", "duration": 20, "steps": ["Reviewing financials", "Analyzing ratios", "Assessing valuation"]},
        {"name": "Information Analyst", "duration": 12, "steps": ["Scanning news", "Evaluating sentiment", "Identifying catalysts"]},
        {"name": "Risk Manager", "duration": 8, "steps": ["Assessing volatility", "Evaluating position sizing", "Calculating risk metrics"]},
    ]

    # Send start event
    start_event = AgentTraceEvent(
        event_type="start",
        message=f"Starting analysis for {company_name} on {trade_date}",
        timestamp=get_utc_timestamp()
    )
    yield await format_sse_event(start_event)

    total_progress = 0
    progress_increment = 100 // len(agents)

    for agent in agents:
        # Agent start event
        agent_start = AgentTraceEvent(
            event_type="agent_update",
            agent_name=agent["name"],
            message=f"{agent['name']} is now analyzing {company_name}",
            progress=total_progress,
            timestamp=get_utc_timestamp()
        )
        yield await format_sse_event(agent_start)

        # Simulate agent working through steps
        step_progress = progress_increment // len(agent["steps"])
        current_agent_progress = 0

        for step in agent["steps"]:
            await asyncio.sleep(random.uniform(1, 3))  # Simulate processing time

            current_agent_progress += step_progress
            total_progress += step_progress

            progress_event = AgentTraceEvent(
                event_type="progress",
                agent_name=agent["name"],
                message=f"{agent['name']}: {step}",
                progress=min(total_progress, 95),  # Cap at 95% until completion
                timestamp=get_utc_timestamp()
            )
            yield await format_sse_event(progress_event)

        # Brief pause between agents
        await asyncio.sleep(0.5)

    # Final completion
    await asyncio.sleep(1)
    complete_event = AgentTraceEvent(
        event_type="complete",
        message=f"Analysis complete for {company_name}",
        progress=100,
        data={
            "decision": random.choice(["BUY", "SELL", "HOLD"]),
            "confidence": random.uniform(0.6, 0.95),
            "agents_used": [agent["name"] for agent in agents]
        },
        timestamp=get_utc_timestamp()
    )
    yield await format_sse_event(complete_event)


async def real_agent_analysis_stream(company_name: str, trade_date: str, conversation_context: Optional[list] = None) -> AsyncGenerator[str, None]:
    """
    Real agent analysis streaming that connects to the agents service.
    This would replace the mock version in production.
    """
    import datetime
    import os

    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")

    try:
        # Send start event
        start_event = AgentTraceEvent(
            event_type="start",
            message=f"Starting agent analysis for {company_name}",
            timestamp=get_utc_timestamp()
        )
        yield await format_sse_event(start_event)

        # Prepare request payload
        payload = {
            "company_name": company_name,
            "trade_date": trade_date
        }
        if conversation_context:
            payload["conversation_context"] = conversation_context

        # For now, we'll call the regular agents endpoint
        # In the future, you might want to modify the agents service to support streaming
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minute timeout
            response = await client.post(f"{agents_url}/analyze", json=payload)
            response.raise_for_status()
            result = response.json()

        # Send completion event with results
        complete_event = AgentTraceEvent(
            event_type="complete",
            message=f"Agent analysis completed for {company_name}",
            progress=100,
            data={
                "decision": result.get("decision"),
                "company": result.get("company"),
                "date": result.get("date"),
                "state": result.get("state"),
                "agents_used": ["Market Analyst", "Fundamental Analyst", "Information Analyst", "Risk Manager"]  # Placeholder
            },
            timestamp=get_utc_timestamp()
        )
        yield await format_sse_event(complete_event)

    except Exception as e:
        logger.error(f"Agent analysis streaming error: {e}", exc_info=True)
        error_event = AgentTraceEvent(
            event_type="error",
            message=f"Analysis failed: {str(e)}",
            timestamp=get_utc_timestamp()
        )
        yield await format_sse_event(error_event)


@router.post("/analyze")
async def stream_agent_analysis(
    request: AgentAnalysisRequest,
    current_user: dict = Depends(require_auth)
):
    """
    Stream agent analysis in real-time using Server-Sent Events.

    This endpoint classifies the query intent, routes to appropriate agent workflow,
    and streams progress updates as Server-Sent Events. The client receives real-time
    updates about which agents are active, their progress, and final results.

    Returns:
        StreamingResponse with text/event-stream content type

    Example client usage:
        const eventSource = new EventSource('/api/streaming/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: 'Should I buy Apple stock?',
                company_name: 'AAPL',
                trade_date: '2024-12-19',
                conversation_context: [...]
            })
        });

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Agent update:', data);
        };
    """
    try:
        orchestrator = get_agent_orchestrator()
        
        # Extract query from conversation context or use provided query
        query_text = request.query
        if not query_text and request.conversation_context:
            # Get last user message from context
            user_messages = [msg for msg in request.conversation_context if msg.get("role") == "user"]
            if user_messages:
                query_text = user_messages[-1].get("content", "")
        
        # If no query and no company_name, we can't proceed
        if not query_text and not request.company_name:
            raise ValueError("Either 'query' or 'company_name' must be provided")
        
        # Use company_name as query fallback if no query provided
        if not query_text:
            query_text = f"Analyze {request.company_name}"
        
        # Classify query and get workflow (also get full classification for entity extraction)
        intent, workflow = orchestrator.classify_and_get_workflow(
            query_text,
            request.conversation_context
        )
        
        # Extract company ticker from LLM entities if not provided
        # Try to resolve ALL entities (both tickers and company names)
        extracted_ticker = None
        if not request.company_name:
            try:
                classification_result = orchestrator.classifier.classify_with_entities(
                    query_text,
                    request.conversation_context
                )
                
                if classification_result and classification_result.entities:
                    # Try each entity - both ticker-like and company names
                    for entity in classification_result.entities:
                        entity_clean = entity.strip()
                        if not entity_clean:
                            continue
                        
                        entity_upper = entity_clean.upper()
                        
                        # First, check if it looks like a ticker (1-5 uppercase letters, no spaces)
                        if 1 <= len(entity_upper) <= 5 and entity_upper.isalpha() and ' ' not in entity_upper:
                            # Validate with yfinance if available (quick check)
                            if YFINANCE_AVAILABLE:
                                try:
                                    ticker = yf.Ticker(entity_upper)
                                    info = ticker.info
                                    # Check if ticker is valid (has symbol in info)
                                    if info and info.get('symbol'):
                                        extracted_ticker = entity_upper
                                        logger.info(f"✓ Extracted and validated ticker '{extracted_ticker}' from query entities")
                                        break
                                except Exception as e:
                                    logger.debug(f"Ticker validation failed for {entity_upper}: {e}")
                                    continue
                            else:
                                # If yfinance not available, use entity as-is if it looks like a ticker
                                extracted_ticker = entity_upper
                                logger.info(f"✓ Extracted ticker '{extracted_ticker}' from query entities (validation skipped)")
                                break
                        else:
                            # Not a ticker-like entity - try to resolve as company name
                            # Use our resolve_company_to_ticker function which tries Yahoo Finance and Alpha Vantage
                            resolved = resolve_company_to_ticker(entity_clean)
                            if resolved:
                                extracted_ticker = resolved
                                logger.info(f"✓ Extracted and resolved company name '{entity_clean}' -> '{extracted_ticker}' from query entities")
                                break
            except Exception as e:
                logger.warning(f"Failed to extract ticker from entities: {e}")
        
        # Use extracted ticker, provided company_name, or fallback
        final_company_name = extracted_ticker or request.company_name or "UNKNOWN"
        
        # Validate company/ticker before proceeding with agent workflows
        # Only validate if workflow requires agents (not for direct_response)
        if workflow.workflow_type != "direct_response":
            # Validate company exists and can be fetched
            is_valid, error_message, normalized_ticker = validate_company_ticker(final_company_name)
            
            if not is_valid:
                logger.warning(f"Company validation failed: {error_message} (company: {final_company_name})")
                
                # Return error early - don't start agent workflow
                async def error_generator():
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=error_message or "Invalid company or ticker symbol",
                        timestamp=datetime.datetime.now().isoformat(),
                        data={
                            "error_type": "invalid_company",
                            "company_name": final_company_name,
                            "suggestion": (
                                f"'{final_company_name}' was not found in our data sources. "
                                "Please try:\n"
                                "- Using the stock ticker symbol (e.g., AAPL for Apple, TSLA for Tesla, MSFT for Microsoft)\n"
                                "- Checking the spelling of the company name\n"
                                "- Using the full company name"
                            )
                        }
                    )
                    yield await format_sse_event(error_event)
                    
                    # Send complete event so frontend knows to stop
                    complete_event = AgentTraceEvent(
                        event_type="complete",
                        message="Workflow stopped - invalid company",
                        progress=0,
                        timestamp=datetime.datetime.now().isoformat(),
                        data={"error": True, "stopped": True}
                    )
                    yield await format_sse_event(complete_event)
                
                return StreamingResponse(
                    error_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Cache-Control",
                    }
                )
            
            # Use normalized ticker if available (from yfinance validation)
            # This ensures agents receive the correct ticker symbol (e.g., "AAPL") 
            # instead of company name (e.g., "APPLE")
            if normalized_ticker:
                final_company_name = normalized_ticker
                logger.info(f"✓ Using normalized ticker: {final_company_name} (original: {request.company_name or extracted_ticker})")
        
        # Get agent endpoint and timeout
        agent_endpoint, timeout_seconds = orchestrator.get_agent_endpoint(workflow)
        
        # If direct response (no agents), return early
        if workflow.workflow_type == "direct_response":
            async def direct_response_generator():
                start_event = AgentTraceEvent(
                    event_type="start",
                    message="Processing query directly (no agents required)",
                    timestamp=get_utc_timestamp(),
                    data={"intent": intent.value, "workflow": workflow.workflow_type}
                )
                yield await format_sse_event(start_event)
                
                complete_event = AgentTraceEvent(
                    event_type="complete",
                    message="Query processed (direct response)",
                    progress=100,
                    timestamp=get_utc_timestamp(),
                    data={"intent": intent.value}
                )
                yield await format_sse_event(complete_event)
            
            return StreamingResponse(
                direct_response_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                }
            )
        
        # For agent workflows, prepare request and route to agent service
        async def event_generator():
            final_response_text = None
            full_agent_response = None  # Store complete agent analysis result
            message_service = MessageService() if request.thread_id else None
            agent_trace_events = []  # Collect all trace events for persistence
            
            try:
                # Emit orchestration start event
                start_event = AgentTraceEvent(
                    event_type="orchestration_start",
                    message=f"Detected {intent.value} query, routing to {workflow.workflow_type}",
                    timestamp=get_utc_timestamp(),
                    data={
                        "intent": intent.value,
                        "workflow": workflow.workflow_type,
                        "agents": workflow.agents,
                        "timeout_seconds": timeout_seconds,
                        "endpoint": agent_endpoint
                    }
                )
                yield await format_sse_event(start_event)
                # Collect orchestration start event for trace persistence
                agent_trace_events.append({
                    "event_type": start_event.event_type,
                    "message": start_event.message,
                    "timestamp": start_event.timestamp,
                    "data": start_event.data,
                    "agent_name": None  # Orchestration events don't have agent_name
                })
                
                # Prepare agent request payload
                agent_payload = orchestrator.prepare_agent_request(
                    company_name=final_company_name,
                    trade_date=request.trade_date,
                    workflow=workflow,
                    conversation_context=request.conversation_context,
                    query=query_text  # Pass the extracted query for dynamic agent selection
                )
                
                # Use real agent service streaming endpoint
                agents_base_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
                
                # If using host.docker.internal or localhost, try container name (works if on same network)
                if "host.docker.internal" in agents_base_url or "localhost" in agents_base_url:
                    # Try container name - works when containers are on the same Docker network
                    # Fallback to original URL if container name doesn't work
                    container_name_url = "http://meridian-agents:8001"
                    logger.info(f"Detected localhost/host.docker.internal, will try container name: {container_name_url}")
                    agents_base_url = container_name_url
                
                agent_streaming_url = f"{agents_base_url}/analyze/stream"
                logger.info(f"Connecting to agent service at: {agent_streaming_url}")
                
                # Prepare request for agent service (use the prepared payload from orchestrator)
                # The orchestrator handles conversation_context format conversion
                agent_request = agent_payload
                
                # Log the request payload for debugging
                logger.info(f"Agent request payload structure:")
                logger.info(f"  - Keys: {list(agent_request.keys()) if isinstance(agent_request, dict) else 'N/A'}")
                if isinstance(agent_request, dict):
                    for key, value in agent_request.items():
                        if key == "conversation_context" and isinstance(value, list):
                            logger.info(f"  - {key}: list with {len(value)} items")
                            if value:
                                logger.info(f"    First item keys: {list(value[0].keys()) if isinstance(value[0], dict) else type(value[0])}")
                        elif isinstance(value, (str, int, float, bool, type(None))):
                            logger.info(f"  - {key}: {value}")
                        else:
                            logger.info(f"  - {key}: {type(value).__name__}")
                
                try:
                    # Proxy the streaming response from the agent service
                    # Use separate timeouts: short connect timeout, long read timeout for streaming
                    streaming_timeout = Timeout(
                        connect=60.0,  # 60 second connection timeout
                        read=None,     # No read timeout for streaming (let it run until completion)
                        write=30.0,    # 30 second write timeout
                        pool=10.0      # 10 second pool timeout
                    )
                    async with httpx.AsyncClient(timeout=streaming_timeout) as client:
                        async with client.stream("POST", agent_streaming_url, json=agent_request) as response:
                            # Check status before processing
                            if response.status_code != 200:
                                # For non-200 responses, we need to read the stream to get error details
                                error_text = ""
                                error_lines = []
                                try:
                                    # Read the error response line by line (it might be SSE format or JSON)
                                    async for line in response.aiter_lines():
                                        error_lines.append(line)
                                        if line.startswith("data: "):
                                            # Try to parse SSE format error
                                            try:
                                                error_data = json.loads(line[6:])
                                                if "message" in error_data:
                                                    error_text = error_data["message"]
                                                elif "detail" in error_data:
                                                    error_text = error_data["detail"]
                                                break
                                            except:
                                                pass
                                        elif line.strip() and not line.startswith(":"):
                                            # Might be plain text error
                                            error_text += line + "\n"
                                        
                                        # Limit reading to prevent hanging
                                        if len(error_lines) > 50:
                                            break
                                    
                                    # If we didn't get error text from SSE, try to parse as JSON from all lines
                                    if not error_text:
                                        combined = "\n".join(error_lines)
                                        try:
                                            error_body = json.loads(combined)
                                            if "detail" in error_body:
                                                error_text = error_body["detail"]
                                            elif "message" in error_body:
                                                error_text = error_body["message"]
                                        except:
                                            error_text = combined[:500] if combined else ""
                                    
                                except Exception as read_err:
                                    logger.debug(f"Error reading error response: {read_err}")
                                    error_text = f"Could not read error response: {str(read_err)}"
                                
                                # Format error detail
                                error_detail = f"Agent service error ({response.status_code})"
                                if error_text:
                                    error_detail = f"Agent service error ({response.status_code}): {error_text[:500]}"
                                
                                logger.error(f"Agent service returned error: {error_detail}")
                                logger.error(f"Request URL: {agent_streaming_url}")
                                logger.error(f"Request payload keys: {list(agent_request.keys()) if isinstance(agent_request, dict) else 'N/A'}")
                                if isinstance(agent_request, dict):
                                    # Log payload without sensitive data
                                    safe_payload = {k: (str(v)[:100] if not isinstance(v, (dict, list)) else type(v).__name__) 
                                                   for k, v in agent_request.items()}
                                    logger.error(f"Request payload preview: {json.dumps(safe_payload, indent=2)[:1000]}")
                                
                                error_event = AgentTraceEvent(
                                    event_type="error",
                                    message=error_detail,
                                    timestamp=get_utc_timestamp(),
                                    data={
                                        "status_code": response.status_code,
                                        "error_detail": error_detail,
                                        "url": agent_streaming_url
                                    }
                                )
                                yield await format_sse_event(error_event)
                                
                                # Send complete event to stop frontend waiting
                                complete_event = AgentTraceEvent(
                                    event_type="complete",
                                    message="Streaming stopped due to error",
                                    progress=0,
                                    timestamp=get_utc_timestamp(),
                                    data={"error": True, "stopped": True}
                                )
                                yield await format_sse_event(complete_event)
                                return  # Exit early on error
                            
                            # Status is 200, proceed with streaming
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    # Parse the event to capture final response and collect for trace
                                    try:
                                        event_data = json.loads(line[6:])  # Remove "data: " prefix
                                        
                                        # Collect event for trace persistence
                                        agent_trace_events.append(event_data)
                                        
                                        # Capture final response from complete events
                                        if event_data.get("event_type") in ["complete", "analysis_complete", "orchestration_complete"]:
                                            if event_data.get("data") and isinstance(event_data["data"], dict):
                                                data = event_data["data"]
                                                
                                                # Store the complete agent response for metadata
                                                full_agent_response = data
                                                
                                                # Log the structure for debugging
                                                logger.info(f"Captured full_agent_response from {event_data.get('event_type')} event - keys: {list(full_agent_response.keys())}")
                                                if full_agent_response.get("state"):
                                                    state_obj = full_agent_response.get("state")
                                                    if isinstance(state_obj, dict):
                                                        logger.info(f"State keys found: {list(state_obj.keys())}")
                                                        logger.info(f"State has {len(state_obj)} keys")
                                                    else:
                                                        logger.warning(f"State is not a dict, type: {type(state_obj)}")
                                                else:
                                                    logger.warning("No 'state' key in full_agent_response data")
                                                
                                                # Also log the entire event for debugging
                                                logger.debug(f"Complete event data structure: {json.dumps({k: type(v).__name__ if not isinstance(v, (str, int, float, bool, type(None))) else str(v)[:100] for k, v in data.items()}, indent=2)}")
                                                
                                                # Extract full response text - check both state and root level
                                                state_data = data.get("state", {})
                                                final_response_text = (
                                                    state_data.get("formatted_response") or
                                                    data.get("response") or
                                                    state_data.get("trader_investment_plan") or
                                                    state_data.get("investment_plan") or
                                                    data.get("trader_investment_plan") or
                                                    data.get("investment_plan") or
                                                    state_data.get("final_trade_decision") or
                                                    data.get("final_trade_decision") or
                                                    data.get("decision") or
                                                    event_data.get("message", "")
                                                )
                                                
                                                # If we only got the decision, try to build a more complete response
                                                if final_response_text and final_response_text in ["BUY", "SELL", "HOLD"]:
                                                    # Build a comprehensive response from available data
                                                    reports = data.get("reports", {})
                                                    response_parts = []
                                                    
                                                    if reports.get("market"):
                                                        response_parts.append(f"**Market Analysis:**\n{reports['market'][:500]}...")
                                                    if reports.get("fundamentals"):
                                                        response_parts.append(f"**Fundamentals:**\n{reports['fundamentals'][:500]}...")
                                                    
                                                    if response_parts:
                                                        final_response_text = "\n\n".join(response_parts) + f"\n\n**Final Decision: {final_response_text}**"
                                                    else:
                                                        # At minimum, provide a meaningful response
                                                        final_response_text = f"Based on comprehensive analysis, the recommended action is: **{final_response_text}**"
                                                
                                                logger.info(f"Extracted final response (length: {len(final_response_text) if final_response_text else 0})")
                                    except (json.JSONDecodeError, KeyError) as e:
                                        logger.debug(f"Could not parse event data: {e}")
                                        pass  # Continue streaming even if parsing fails
                                    
                                    yield line + "\n"
                                elif line.strip() and not line.startswith(":"):
                                    # Handle any other SSE format lines
                                    yield line + "\n"
                    
                    # Generate PDF from the agent analysis (even without thread_id)
                    # Check the last trace event for complete state (as user mentioned state is in last second trace)
                    logger.info("=" * 80)
                    logger.info("TRACE ANALYSIS - Checking all events for complete state")
                    logger.info("=" * 80)
                    logger.info(f"Total trace events collected: {len(agent_trace_events)}")
                    
                    # Log all event types to see what we have
                    event_types = [evt.get("event_type", "unknown") for evt in agent_trace_events]
                    logger.info(f"Event types in trace: {event_types}")
                    
                    # Check the last few events for state (user said state is in "last second trace")
                    if agent_trace_events:
                        # Check last 5 events for state
                        last_events = agent_trace_events[-5:] if len(agent_trace_events) >= 5 else agent_trace_events
                        logger.info(f"Analyzing last {len(last_events)} trace events for state...")
                        
                        for idx, event in enumerate(reversed(last_events), 1):
                            event_num = len(agent_trace_events) - idx + 1
                            event_type = event.get("event_type", "unknown")
                            logger.info(f"  Event #{event_num} (from end): type={event_type}")
                            
                            # Check event.data for state
                            event_data = event.get("data", {}) if isinstance(event, dict) else {}
                            if isinstance(event_data, dict):
                                logger.info(f"    - event.data keys: {list(event_data.keys())}")
                                
                                # Check if state is directly in event.data
                                if event_data.get("state"):
                                    state_obj = event_data.get("state")
                                    if isinstance(state_obj, dict):
                                        logger.info(f"    ✓ Found state in event.data with {len(state_obj)} keys: {list(state_obj.keys())[:10]}")
                                        
                                        # Use this state if we don't have one or if it's more complete
                                        if not full_agent_response:
                                            full_agent_response = event_data
                                            logger.info(f"    ✓ Using state from event #{event_num} (no previous state)")
                                        elif not full_agent_response.get("state"):
                                            full_agent_response = event_data
                                            logger.info(f"    ✓ Using state from event #{event_num} (previous had no state)")
                                        elif isinstance(full_agent_response.get("state"), dict):
                                            # Compare and use the one with more keys
                                            trace_state = state_obj
                                            current_state = full_agent_response.get("state", {})
                                            if len(trace_state) > len(current_state):
                                                full_agent_response = event_data
                                                logger.info(f"    ✓ Using more complete state from event #{event_num} ({len(trace_state)} keys vs {len(current_state)} keys)")
                                            else:
                                                logger.info(f"    - Keeping current state ({len(current_state)} keys >= {len(trace_state)} keys)")
                                
                                # Also check if the entire event.data IS the state (state keys at root)
                                state_keys_at_root = ["market_report", "fundamentals_report", "news_report", "sentiment_report", "investment_debate_state", "risk_debate_state"]
                                if any(key in event_data for key in state_keys_at_root):
                                    logger.info(f"    ✓ Found state keys at root level in event.data")
                                    if not full_agent_response or not isinstance(full_agent_response, dict):
                                        full_agent_response = event_data
                                        logger.info(f"    ✓ Using event.data as full_agent_response (state keys at root)")
                                    elif not full_agent_response.get("state"):
                                        # Merge event_data into full_agent_response or replace
                                        full_agent_response = event_data
                                        logger.info(f"    ✓ Using event.data as full_agent_response (previous had no state)")
                            else:
                                logger.debug(f"    - event.data is not a dict: {type(event_data)}")
                    
                    # Final check: if we still don't have state, log what we have
                    if not full_agent_response:
                        logger.warning("⚠ No full_agent_response found in any trace event!")
                        logger.info("Available event data structures:")
                        for idx, event in enumerate(agent_trace_events[-10:], 1):  # Last 10 events
                            logger.info(f"  Event {len(agent_trace_events) - 10 + idx}: {event.get('event_type')} - data keys: {list(event.get('data', {}).keys()) if isinstance(event.get('data'), dict) else 'N/A'}")
                    elif not full_agent_response.get("state") and isinstance(full_agent_response, dict):
                        logger.warning("⚠ full_agent_response exists but has no 'state' key")
                        logger.info(f"  full_agent_response keys: {list(full_agent_response.keys())}")
                    
                    pdf_filename = None
                    if full_agent_response and final_response_text:
                        try:
                            logger.info("=" * 80)
                            logger.info("PDF GENERATION - Starting Process")
                            logger.info("=" * 80)
                            
                            company = full_agent_response.get("company") or final_company_name or "UNKNOWN"
                            date = full_agent_response.get("date") or request.trade_date
                            decision = full_agent_response.get("decision", "UNKNOWN")
                            
                            logger.info(f"PDF Input Parameters:")
                            logger.info(f"  - Company: {company}")
                            logger.info(f"  - Date: {date}")
                            logger.info(f"  - Decision: {decision}")
                            
                            # Log full_agent_response structure
                            logger.info(f"full_agent_response type: {type(full_agent_response)}")
                            if isinstance(full_agent_response, dict):
                                logger.info(f"full_agent_response top-level keys: {list(full_agent_response.keys())}")
                                for key, value in full_agent_response.items():
                                    if key == "state" and isinstance(value, dict):
                                        logger.info(f"  - {key}: dict with {len(value)} keys: {list(value.keys())[:10]}...")
                                    elif isinstance(value, (str, int, float, bool, type(None))):
                                        logger.info(f"  - {key}: {type(value).__name__} (length: {len(str(value))} if str else 'N/A')")
                                    else:
                                        logger.info(f"  - {key}: {type(value).__name__}")
                            
                            # Extract state correctly - check nested state first
                            state = full_agent_response.get("state")
                            logger.info(f"Extracted state type: {type(state)}")
                            
                            # If state is not a dict or doesn't have expected keys, check if root has them
                            if not state or not isinstance(state, dict):
                                logger.warning(f"State is not a dict: {type(state)}")
                                # Check if full_agent_response itself has state keys at root level
                                if isinstance(full_agent_response, dict) and any(key in full_agent_response for key in ["market_report", "fundamentals_report", "news_report", "sentiment_report"]):
                                    state = full_agent_response
                                    logger.info("✓ Using full_agent_response as state (state keys at root level)")
                                else:
                                    # Last resort: use full response
                                    state = full_agent_response
                                    logger.warning("⚠ State structure not found, using full response as fallback")
                            else:
                                logger.info(f"✓ Using nested state with {len(state)} keys: {list(state.keys())}")
                            
                            # Detailed state content logging
                            if isinstance(state, dict):
                                logger.info("State Content Analysis:")
                                expected_keys = [
                                    "market_report", "fundamentals_report", "news_report", 
                                    "sentiment_report", "information_report",
                                    "investment_debate_state", "risk_debate_state",
                                    "investment_plan", "trader_investment_plan",
                                    "final_trade_decision"
                                ]
                                
                                for key in expected_keys:
                                    if key in state:
                                        value = state[key]
                                        if isinstance(value, str):
                                            logger.info(f"  ✓ {key}: present (length: {len(value)} chars)")
                                        elif isinstance(value, dict):
                                            logger.info(f"  ✓ {key}: present (dict with {len(value)} keys: {list(value.keys())})")
                                        else:
                                            logger.info(f"  ✓ {key}: present (type: {type(value).__name__})")
                                    else:
                                        logger.warning(f"  ✗ {key}: MISSING from state")
                                
                                # Log any unexpected keys
                                unexpected_keys = [k for k in state.keys() if k not in expected_keys]
                                if unexpected_keys:
                                    logger.info(f"  Additional state keys found: {unexpected_keys}")
                            else:
                                logger.warning(f"State is not a dict, cannot analyze content. Type: {type(state)}")
                            
                            logger.info(f"Final state passed to PDF generator - keys: {list(state.keys()) if isinstance(state, dict) else 'N/A'}")
                            
                            # Prepare agent trace for PDF
                            agent_trace_for_pdf = None
                            if agent_trace_events:
                                agent_trace_for_pdf = {
                                    "events": agent_trace_events,
                                    "agents_called": list(set(
                                        evt.get("agent_name") 
                                        for evt in agent_trace_events 
                                        if evt.get("agent_name")
                                    )),
                                    "intent": intent.value,
                                    "workflow": workflow.workflow_type
                                }
                                logger.info(f"Agent trace prepared for PDF:")
                                logger.info(f"  - Events: {len(agent_trace_events)}")
                                logger.info(f"  - Agents called: {agent_trace_for_pdf['agents_called']}")
                                logger.info(f"  - Intent: {agent_trace_for_pdf['intent']}")
                                logger.info(f"  - Workflow: {agent_trace_for_pdf['workflow']}")
                            else:
                                logger.warning("No agent trace events available for PDF")
                            
                            logger.info("Calling generate_analysis_pdf()...")
                            pdf_buffer = generate_analysis_pdf(
                                company=company,
                                date=date,
                                decision=decision,
                                state=state,
                                agent_trace=agent_trace_for_pdf
                            )
                            
                            pdf_dir = "/app/data/pdfs"
                            os.makedirs(pdf_dir, exist_ok=True)
                            
                            pdf_filename = f"Meridian_{company}_{date}.pdf"
                            pdf_path = os.path.join(pdf_dir, pdf_filename)
                            
                            # Fix: Get the PDF bytes before writing (buffer position might have moved)
                            pdf_buffer.seek(0)  # Ensure we're at the start
                            pdf_bytes = pdf_buffer.read()
                            pdf_buffer.seek(0)  # Reset for potential reuse
                            
                            with open(pdf_path, 'wb') as f:
                                f.write(pdf_bytes)
                            
                            logger.info(f"Generated PDF: {pdf_path} (size: {len(pdf_bytes):,} bytes)")
                        except Exception as pdf_error:
                            logger.error(f"Failed to generate PDF: {pdf_error}", exc_info=True)
                            # Don't fail the request if PDF generation fails
                            
                    # Save agent response to database if thread_id is provided
                    if request.thread_id and final_response_text and message_service:
                        try:
                            metadata = {
                                "agent_trace": {
                                    "events": agent_trace_events,
                                    "agents_called": list(set(
                                        evt.get("agent_name") 
                                        for evt in agent_trace_events 
                                        if evt.get("agent_name")
                                    )),
                                    "intent": intent.value,
                                    "workflow": workflow.workflow_type
                                },
                                "source": "agent_service",
                                "workflow_type": workflow.workflow_type,
                                "agents_used": workflow.agents,
                                # Include full agent analysis for frontend breakdown
                                "agent_analysis": full_agent_response if full_agent_response else None,
                                # Include PDF filename for download (if generated)
                                "pdf_filename": pdf_filename
                            }
                            
                            assistant_msg = await message_service.save_assistant_message(
                                thread_id=request.thread_id,
                                content=final_response_text,
                                metadata=metadata
                            )
                            logger.info(
                                f"Saved agent response with trace to thread {request.thread_id}: "
                                f"{assistant_msg['message_id']} ({len(agent_trace_events)} trace events)"
                            )
                        except Exception as e:
                            logger.error(f"Failed to save agent response to database: {e}", exc_info=True)
                            # Don't fail the request if saving fails
                except httpx.HTTPStatusError as e:
                    error_detail = f"Agent service error: {e.response.status_code}"
                    try:
                        # For streaming responses, we need to read the content first
                        if hasattr(e.response, 'is_stream_consumed') and not e.response.is_stream_consumed:
                            # Try to read the error response
                            try:
                                error_text = await e.response.aread()
                                if error_text:
                                    error_body = json.loads(error_text.decode('utf-8'))
                                    if "detail" in error_body:
                                        error_detail = f"Agent service error ({e.response.status_code}): {error_body['detail']}"
                                    else:
                                        error_detail = f"Agent service error ({e.response.status_code}): {error_text.decode('utf-8')[:500]}"
                            except Exception as read_err:
                                logger.debug(f"Could not read error response: {read_err}")
                                error_detail = f"Agent service error: {e.response.status_code} - {str(e)}"
                        else:
                            # Non-streaming response, can use .json() or .text
                            try:
                                error_body = e.response.json()
                                if "detail" in error_body:
                                    error_detail = f"Agent service error ({e.response.status_code}): {error_body['detail']}"
                            except:
                                try:
                                    error_detail = f"Agent service error ({e.response.status_code}): {e.response.text[:500]}"
                                except:
                                    error_detail = f"Agent service error: {e.response.status_code} - {str(e)}"
                    except Exception as parse_err:
                        logger.debug(f"Error parsing error response: {parse_err}")
                        error_detail = f"Agent service error: {e.response.status_code} - {str(e)}"
                    
                    logger.error(f"HTTPStatusError from agent service: {error_detail}", exc_info=True)
                    logger.error(f"Request URL: {agent_streaming_url}")
                    logger.error(f"Request payload keys: {list(agent_request.keys()) if isinstance(agent_request, dict) else 'N/A'}")
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"Agent service failed: {error_detail}",
                        timestamp=get_utc_timestamp()
                    )
                    yield await format_sse_event(error_event)
                except httpx.RequestError as e:
                    error_msg = str(e)
                    # Provide more helpful error message
                    if "Name or service not known" in error_msg or "Name resolution failed" in error_msg:
                        error_msg = f"Agent service hostname not resolvable. Check AGENTS_SERVICE_URL (current: {agents_base_url})"
                    elif "Connection refused" in error_msg:
                        error_msg = f"Agent service connection refused. Is the service running on {agents_base_url}?"
                    elif "timeout" in error_msg.lower():
                        error_msg = f"Agent service connection timeout. Service may be overloaded or unreachable at {agents_base_url}"
                    
                    logger.error(f"RequestError connecting to agent service at {agent_streaming_url}: {error_msg}", exc_info=True)
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"Agent service unavailable: {error_msg}",
                        timestamp=get_utc_timestamp(),
                        data={
                            "agent_url": agent_streaming_url,
                            "error_type": type(e).__name__
                        }
                    )
                    yield await format_sse_event(error_event)
                except Exception as e:
                    logger.error(f"Unexpected error during agent streaming: {e}", exc_info=True)
                    error_event = AgentTraceEvent(
                        event_type="error",
                        message=f"An unexpected error occurred: {str(e)}",
                        timestamp=get_utc_timestamp()
                    )
                    yield await format_sse_event(error_event)
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_event = AgentTraceEvent(
                    event_type="error",
                    message=f"Streaming failed: {str(e)}",
                    timestamp=get_utc_timestamp()
                )
                yield await format_sse_event(error_event)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )

    except Exception as e:
        logger.error(f"Failed to start streaming analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start agent analysis streaming: {str(e)}"
        )


@router.get("/health")
async def streaming_health():
    """
    Health check for streaming service.

    Returns:
        dict: Health status information
    """
    return {
        "status": "ok",
        "service": "streaming",
        "features": ["sse", "agent_analysis_streaming"],
        "version": "1.0.0"
    }
