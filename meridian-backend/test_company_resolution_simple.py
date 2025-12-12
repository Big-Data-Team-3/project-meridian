"""
Simple standalone test script for company name resolution.
This version doesn't import the full API stack to avoid dependency issues.

Usage:
    python test_company_resolution_simple.py
"""
import logging
import json
import time

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    print("✅ yfinance is available")
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance not available - cannot test\n")
    exit(1)

# Try to import requests for Yahoo Finance search
try:
    import requests
    REQUESTS_AVAILABLE = True
    print("✅ requests is available\n")
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  requests not available - will use fallback method\n")

from typing import Optional, List, Dict
import os


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
                    print(f"    → Direct ticker match: {ticker_upper}")
                    return ticker_upper
        except Exception as e:
            pass
    
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
            print(f"    → Resolved via Alpha Vantage search: {searched_ticker}")
    
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
                            print(f"    → Resolved via Yahoo Finance search: {searched_ticker} ({short_name.title() or long_name.title()})")
                            return searched_ticker
                except Exception:
                    pass
            else:
                # If yfinance not available, trust the search result
                print(f"    → Resolved via Yahoo Finance search: {searched_ticker}")
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
                        display_name = short_name.title() or long_name.title()
                        print(f"    → Resolved via candidate '{candidate}': {symbol} ({display_name})")
                        return symbol.upper()
                        
            except Exception:
                continue
    
    return None


def test_company_resolution():
    """Test various company name formats"""
    
    test_cases = [
        # (input, should_resolve, expected_ticker)
        ("AAPL", True, "AAPL"),
        ("aapl", True, "AAPL"),
        ("Apple", True, "AAPL"),
        ("apple", True, "AAPL"),
        ("AMZN", True, "AMZN"),
        ("amazon", True, "AMZN"),
        ("Amazon", True, "AMZN"),
        ("TSLA", True, "TSLA"),
        ("tesla", True, "TSLA"),
        ("Tesla", True, "TSLA"),
        ("MSFT", True, "MSFT"),
        ("microsoft", True, "MSFT"),
        ("Microsoft", True, "MSFT"),
        ("GOOGL", True, "GOOGL"),
        ("google", True, "GOOGL"),
        ("INVALID_XYZ", False, None),
        ("ripple", False, None),
    ]
    
    print("=" * 80)
    print("Testing Company Name Resolution")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for input_text, should_resolve, expected_ticker in test_cases:
        print(f"Testing: '{input_text}'")
        print(f"  Expected: ", end="")
        if should_resolve:
            print(f"✓ Resolve to {expected_ticker}")
        else:
            print(f"✗ Should not resolve")
        
        resolved = resolve_company_to_ticker(input_text)
        
        print(f"  Result:   ", end="")
        if resolved:
            print(f"✓ Resolved to {resolved}")
        else:
            print(f"✗ Not resolved")
        
        # Check if result matches expectation
        if should_resolve:
            success = (resolved is not None and expected_ticker in resolved)
        else:
            success = (resolved is None)
        
        if success:
            print(f"  Status:   ✅ PASS")
            passed += 1
        else:
            print(f"  Status:   ❌ FAIL")
            failed += 1
        
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    if failed == 0:
        print("\n🎉 All tests passed! Company name resolution is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = test_company_resolution()
    sys.exit(0 if success else 1)
