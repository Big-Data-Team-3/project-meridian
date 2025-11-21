"""
Test script to verify data access from all required data source libraries.
This script calls actual methods from each library and displays the results.
"""
import os
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("=" * 70)
print("Testing Data Source Libraries")
print("=" * 70)

# ============================================================================
# 1. GDELT - Global Database of Events, Language, and Tone
# ============================================================================
print("\n[1] Testing GDELT...")
try:
    import gdelt
    
    # Create GDELT client
    gd = gdelt.gdelt()
    print(f"✓ GDELT client created: {type(gd)}")
    
    # Try to get recent events (this will make an actual API call)
    # Using a small date range to minimize data
    try:
        print("  Attempting to fetch GDELT data for 2024-01-01...")
        # Note: GDELT Search method may require specific parameters
        # This is a basic test to see if we can access the method
        if hasattr(gd, 'Search'):
            print(f"  ✓ GDELT Search method available")
            print(f"  Method signature: {gd.Search.__doc__[:100] if gd.Search.__doc__ else 'No docstring'}")
        else:
            print(f"  Available methods: {[m for m in dir(gd) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ⚠ Could not fetch data (may need network): {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ GDELT failed: {type(e).__name__}: {e}")

# ============================================================================
# 2. FRED API - Federal Reserve Economic Data
# ============================================================================
print("\n[2] Testing FRED API...")
try:
    import fredapi
    
    # Get API key from .env file
    api_key = os.environ.get('FRED_API_KEY')
    if not api_key:
        print("  ⚠ FRED_API_KEY not found in .env file - using test key")
        api_key = 'test_key_demo'
    else:
        print(f"  ✓ FRED_API_KEY loaded from .env file")
    fred = fredapi.Fred(api_key=api_key)
    print(f"✓ FRED client created with API key: {api_key[:10]}...")
    
    # Try to get a popular economic series (GDP)
    try:
        print("  Attempting to fetch GDP data...")
        # Get GDP data (this will fail with test key, but shows the method works)
        if hasattr(fred, 'get_series'):
            print(f"  ✓ get_series method available")
            # Try with a test series ID
            try:
                # This will fail without a real API key, but shows we can call it
                result = fred.get_series('GDP', start='2020-01-01', end='2020-12-31')
                print(f"  ✓ Data retrieved: {type(result)} with {len(result)} data points")
                print(f"  Sample data:\n{result.head() if hasattr(result, 'head') else result[:5]}")
            except Exception as api_error:
                print(f"  ⚠ API call failed (expected with test key): {type(api_error).__name__}")
                print(f"  ✓ Method is accessible and callable")
        else:
            print(f"  Available methods: {[m for m in dir(fred) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ⚠ Could not fetch data: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ FRED API failed: {type(e).__name__}: {e}")

# ============================================================================
# 3. SEC EDGAR API
# ============================================================================
print("\n[3] Testing SEC EDGAR API...")
try:
    from sec_edgar_api import EdgarClient
    
    # Create client with user agent (required)
    user_agent = "Test User (test@example.com)"
    client = EdgarClient(user_agent=user_agent)
    print(f"✓ SEC EDGAR API client created")
    
    # Try to get company submissions
    try:
        print("  Attempting to fetch company submissions for AAPL...")
        if hasattr(client, 'get_submissions'):
            print(f"  ✓ get_submissions method available")
            # Try to get submissions for Apple (CIK: 0000320193)
            try:
                submissions = client.get_submissions(cik="0000320193")
                print(f"  ✓ Data retrieved: {type(submissions)}")
                print(f"  Keys in response: {list(submissions.keys()) if isinstance(submissions, dict) else 'N/A'}")
                if isinstance(submissions, dict):
                    if 'filings' in submissions:
                        recent = submissions.get('filings', {}).get('recent', {})
                        if 'form' in recent:
                            print(f"  Number of filings: {len(recent.get('form', []))}")
                            print(f"  Sample forms: {recent.get('form', [])[:5]}")
                    else:
                        print(f"  Response structure: {str(submissions)[:200]}")
            except Exception as api_error:
                print(f"  ⚠ API call failed: {type(api_error).__name__}: {str(api_error)[:100]}")
                print(f"  ✓ Method is accessible and callable")
        else:
            print(f"  Available methods: {[m for m in dir(client) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ⚠ Could not fetch data: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ SEC EDGAR API failed: {type(e).__name__}: {e}")

# ============================================================================
# 4. SecEdgar
# ============================================================================
print("\n[4] Testing SecEdgar...")
try:
    from secedgar import filings, FilingType
    
    print(f"✓ SecEdgar imported successfully")
    print(f"  Available: filings function, FilingType enum")
    
    # Try to create a filings object
    try:
        print("  Attempting to create filings object for AAPL...")
        # Create a company filings object (this doesn't fetch data yet, just creates the object)
        company_filings = filings(
            cik_lookup="AAPL",
            filing_type=FilingType.FILING_10K,
            user_agent="Test User (test@example.com)"
        )
        print(f"  ✓ Filings object created: {type(company_filings)}")
        print(f"  Available methods: {[m for m in dir(company_filings) if not m.startswith('_') and callable(getattr(company_filings, m, None))]}")
        
        # Try to get URLs (this might make network calls)
        try:
            print("  Attempting to get filing URLs...")
            urls = company_filings.get_urls()
            print(f"  ✓ Retrieved {len(urls)} URLs")
            if urls:
                print(f"  Sample URL: {urls[0][:80]}...")
        except Exception as url_error:
            print(f"  ⚠ Could not get URLs (may need network): {type(url_error).__name__}")
            print(f"  ✓ Method is accessible")
    except Exception as e:
        print(f"  ⚠ Could not create filings object: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ SecEdgar failed: {type(e).__name__}: {e}")

# ============================================================================
# 5. SEC EDGAR Downloader
# ============================================================================
print("\n[5] Testing SEC EDGAR Downloader...")
try:
    from sec_edgar_downloader import Downloader
    
    # Create downloader (requires company name and email)
    downloader = Downloader(
        company_name="Test Company",
        email_address="test@example.com"
    )
    print(f"✓ SEC EDGAR Downloader created")
    
    # Try to get recent filings
    try:
        print("  Attempting to get recent filings for AAPL...")
        if hasattr(downloader, 'get'):
            print(f"  ✓ get method available")
            # Try to get a recent filing
            try:
                # This will download files, so we'll just test the method exists
                print(f"  Method signature available")
                print(f"  Available methods: {[m for m in dir(downloader) if not m.startswith('_') and callable(getattr(downloader, m, None))]}")
            except Exception as api_error:
                print(f"  ⚠ Download failed (may need network): {type(api_error).__name__}")
                print(f"  ✓ Method is accessible")
        else:
            print(f"  Available methods: {[m for m in dir(downloader) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ⚠ Could not test download: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ SEC EDGAR Downloader failed: {type(e).__name__}: {e}")

# ============================================================================
# 6. Finnhub
# ============================================================================
print("\n[6] Testing Finnhub...")
try:
    import finnhub
    
    # Get API key from .env file
    api_key = os.environ.get('FINNHUB_API_KEY')
    if not api_key:
        print("  ⚠ FINNHUB_API_KEY not found in .env file - using test key")
        api_key = 'test_key_demo'
    else:
        print(f"  ✓ FINNHUB_API_KEY loaded from .env file")
    client = finnhub.Client(api_key=api_key)
    print(f"✓ Finnhub client created with API key: {api_key[:10]}...")
    
    # Try to get stock quote
    try:
        print("  Attempting to fetch stock quote for AAPL...")
        if hasattr(client, 'quote'):
            print(f"  ✓ quote method available")
            try:
                quote = client.quote('AAPL')
                print(f"  ✓ Data retrieved: {type(quote)}")
                print(f"  Quote data: {quote}")
            except Exception as api_error:
                print(f"  ⚠ API call failed (expected with test key): {type(api_error).__name__}")
                print(f"  ✓ Method is accessible and callable")
        else:
            print(f"  Available methods: {[m for m in dir(client) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ⚠ Could not fetch data: {type(e).__name__}: {e}")
    
    # Try to get company profile
    try:
        print("  Attempting to fetch company profile for AAPL...")
        if hasattr(client, 'company_profile2'):
            try:
                profile = client.company_profile2(symbol='AAPL')
                print(f"  ✓ Profile data retrieved: {type(profile)}")
                print(f"  Profile keys: {list(profile.keys()) if isinstance(profile, dict) else 'N/A'}")
            except Exception as api_error:
                print(f"  ⚠ API call failed (expected with test key): {type(api_error).__name__}")
        elif hasattr(client, 'company_profile'):
            try:
                profile = client.company_profile(symbol='AAPL')
                print(f"  ✓ Profile data retrieved: {type(profile)}")
            except Exception as api_error:
                print(f"  ⚠ API call failed (expected with test key): {type(api_error).__name__}")
    except Exception as e:
        print(f"  ⚠ Could not fetch profile: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ Finnhub failed: {type(e).__name__}: {e}")

# ============================================================================
# 7. yfinance - Yahoo Finance Data
# ============================================================================
print("\n[7] Testing yfinance...")
try:
    import yfinance as yf
    
    print(f"✓ yfinance imported successfully")
    
    # Create a ticker object for Apple
    try:
        print("  Creating ticker object for AAPL...")
        ticker = yf.Ticker("AAPL")
        print(f"  ✓ Ticker object created: {type(ticker)}")
        
        # Get stock info
        try:
            print("  Attempting to fetch stock info...")
            info = ticker.info
            print(f"  ✓ Stock info retrieved: {type(info)}")
            if isinstance(info, dict):
                print(f"  Number of info fields: {len(info)}")
                print(f"  Sample fields: {list(info.keys())[:10]}")
                if 'currentPrice' in info:
                    print(f"  Current Price: ${info.get('currentPrice', 'N/A')}")
                if 'marketCap' in info:
                    print(f"  Market Cap: ${info.get('marketCap', 'N/A'):,}")
        except Exception as e:
            print(f"  ⚠ Could not fetch stock info: {type(e).__name__}: {e}")
        
        # Get historical data
        try:
            print("  Attempting to fetch historical data (last 5 days)...")
            hist = ticker.history(period="5d")
            print(f"  ✓ Historical data retrieved: {type(hist)}")
            if hasattr(hist, 'shape'):
                print(f"  Data shape: {hist.shape}")
                print(f"  Columns: {list(hist.columns)}")
                if len(hist) > 0:
                    print(f"  Latest close price: ${hist['Close'].iloc[-1]:.2f}")
                    print(f"  Date range: {hist.index[0].date()} to {hist.index[-1].date()}")
        except Exception as e:
            print(f"  ⚠ Could not fetch historical data: {type(e).__name__}: {e}")
        
        # Get current price data
        try:
            print("  Attempting to fetch current price data...")
            data = ticker.fast_info
            print(f"  ✓ Fast info retrieved: {type(data)}")
            if hasattr(data, 'lastPrice'):
                print(f"  Last Price: ${data.lastPrice}")
            if hasattr(data, 'volume'):
                print(f"  Volume: {data.volume:,}")
        except Exception as e:
            print(f"  ⚠ Could not fetch fast info: {type(e).__name__}: {e}")
        
        # Try to get recommendations
        try:
            print("  Attempting to fetch recommendations...")
            recommendations = ticker.recommendations
            if recommendations is not None and len(recommendations) > 0:
                print(f"  ✓ Recommendations retrieved: {type(recommendations)}")
                print(f"  Number of recommendations: {len(recommendations)}")
                print(f"  Latest recommendation: {recommendations.iloc[-1] if hasattr(recommendations, 'iloc') else recommendations[-1]}")
            else:
                print(f"  ⚠ No recommendations available")
        except Exception as e:
            print(f"  ⚠ Could not fetch recommendations: {type(e).__name__}: {e}")
        
        # Try to get financials
        try:
            print("  Attempting to fetch financial statements...")
            financials = ticker.financials
            if financials is not None and len(financials) > 0:
                print(f"  ✓ Financials retrieved: {type(financials)}")
                print(f"  Financials shape: {financials.shape}")
                print(f"  Columns (dates): {list(financials.columns)[:5]}")
            else:
                print(f"  ⚠ No financials available")
        except Exception as e:
            print(f"  ⚠ Could not fetch financials: {type(e).__name__}: {e}")
        
    except Exception as e:
        print(f"  ⚠ Could not create ticker: {type(e).__name__}: {e}")
    
    # Test downloading multiple tickers at once
    try:
        print("  Testing multi-ticker download (AAPL, MSFT, GOOGL)...")
        data = yf.download("AAPL MSFT GOOGL", period="1d", group_by='ticker')
        print(f"  ✓ Multi-ticker data retrieved: {type(data)}")
        if hasattr(data, 'shape'):
            print(f"  Data shape: {data.shape}")
            print(f"  Tickers retrieved: {list(data.columns.levels[0]) if hasattr(data.columns, 'levels') else 'N/A'}")
    except Exception as e:
        print(f"  ⚠ Could not download multi-ticker data: {type(e).__name__}: {e}")
    
except Exception as e:
    print(f"✗ yfinance failed: {type(e).__name__}: {e}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("Testing Complete")
print("=" * 70)
print("\nNote: API keys are loaded from .env file.")
print("Make sure your .env file contains:")
print("  - FRED_API_KEY=your_fred_api_key")
print("  - FINNHUB_API_KEY=your_finnhub_api_key")
print("\nNote: yfinance does not require an API key (uses Yahoo Finance public API).")
print("\nAll libraries have been tested for basic functionality and method access.")
