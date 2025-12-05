## **Financial Data Requirements by Instrument Type**

Based on your Meridian project's goals of building an autonomous multi-agent financial analysis platform, here's the comprehensive data requirements for each instrument type:

### **1. Stocks (Individual Company Securities)**

#### **Required Data:**
- **Price/Volume Data**: Historical OHLCV (Open, High, Low, Close, Volume) - 5+ years
- **Fundamental Data**: Revenue, EPS, P/E, P/B, ROE, ROA, debt ratios, cash flow
- **SEC Filings**: 10-K, 10-Q, 8-K (full text for summarization)
- **Analyst Estimates**: EPS estimates, price targets, recommendations
- **Corporate Actions**: Dividends, splits, mergers, buybacks
- **Options Data**: Implied volatility, open interest, strike prices

#### **Justifications:**
- **Price Data**: Essential for technical analysis, trend detection, and correlation with macroeconomic indicators
- **Fundamentals**: Required for valuation analysis, financial health assessment, and company comparisons
- **SEC Filings**: Your core differentiator - enables automated document summarization and qualitative analysis
- **Analyst Data**: Provides market consensus for validation against LLM-generated insights
- **Options**: Critical for volatility analysis and risk assessment

### **2. ETFs (Exchange-Traded Funds)**

#### **Required Data:**
- **Price/Volume Data**: Historical OHLCV - 5+ years
- **Holdings Data**: Portfolio composition, sector allocations, top holdings
- **ETF-Specific Metrics**: Expense ratio, tracking error, AUM (Assets Under Management)
- **Fund Documents**: Prospectuses, fact sheets, semi-annual reports
- **SEC Filings**: N-CEN, N-CSR, N-Q, N-PORT (ETF-specific forms)
- **Performance Data**: Total return, benchmark comparison, dividend yield

#### **Justifications:**
- **Holdings Data**: Critical for understanding ETF exposure and risk - missing this limits analysis depth
- **ETF Forms**: N-PORT provides monthly portfolio holdings (unlike company 10-Ks)
- **Tracking Data**: Essential for evaluating ETF quality and cost-effectiveness
- **Performance Metrics**: Required for comparative analysis across ETFs and passive vs active strategies

### **3. Indices (Market/Benchmark Indices)**

#### **Required Data:**
- **Index Levels**: Historical values, constituents, weighting methodology
- **Sector Breakdown**: Industry sector allocations and performance
- **Constituent Data**: Individual stock weights, entry/exit dates
- **Economic Indicators**: GDP, inflation, employment (via FRED integration)
- **Market Breadth**: Advance-decline lines, new highs/new lows

#### **Justifications:**
- **Constituent Data**: Enables sector rotation analysis and market breadth studies
- **Economic Context**: Indices reflect macroeconomic conditions - critical for your FRED integration
- **Sector Analysis**: Supports cross-sector performance comparisons and trend analysis

### **4. Macroeconomic Data (FRED Integration)**

#### **Required Data:**
- **Interest Rates**: Fed Funds Rate, Treasury yields (2Y, 10Y, 30Y)
- **Economic Indicators**: GDP, CPI, unemployment, housing starts
- **Financial Conditions**: Credit spreads, VIX, yield curve data
- **Global Data**: Exchange rates, commodity prices, international indicators

#### **Justifications:**
- **Market Context**: Essential for explaining stock/ETF movements beyond company-specific factors
- **Risk Assessment**: Interest rates and inflation drive market volatility
- **Cross-Asset Analysis**: Enables correlation studies between macro factors and asset performance

---

## **Critical Gaps in Current Implementation**

### **What's Missing (High Priority):**

1. **ETF Holdings Data**: Your yfinance client only gets basic info - missing N-PORT filings with monthly holdings
2. **Options Data**: No implied volatility or options chain data for volatility analysis
3. **Analyst Estimates**: Missing consensus estimates for validation
4. **Index Constituents**: No breakdown of what stocks comprise indices
5. **Intraday Data**: Only daily data limits real-time analysis capabilities

### **Impact on Project Goals:**

- **Automated Analysis**: Without holdings data, ETF analysis is superficial
- **Risk Assessment**: Missing options data limits volatility and risk analysis
- **Validation**: No analyst consensus to validate LLM-generated insights
- **Comprehensive Coverage**: Index constituent data needed for sector analysis

---

## **Data Quality Requirements**

### **Temporal Coverage:**
- **Stocks/ETFs**: 5+ years of daily data minimum, 10+ years preferred
- **Indices**: Full history since inception
- **Macro Data**: 20+ years for meaningful trend analysis

### **Update Frequency:**
- **Prices**: Daily EOD data
- **Filings**: Real-time (within hours of SEC filing)
- **Holdings**: Monthly (for ETFs) or quarterly (for mutual funds)

### **Data Freshness:**
- **Trading Data**: <24 hours old
- **Filings**: <1 hour old (for timely analysis)
- **Economic Data**: <1 week old acceptable for most indicators

---

## **Cost-Benefit Analysis**

### **Data Sources to Add (Within Budget):**
1. **ETF Holdings**: SEC EDGAR N-PORT forms (free) - adds 80% more ETF analysis capability
2. **Options Data**: CBOE API or yfinance options (free/low cost) - critical for volatility analysis
3. **Index Constituents**: Free from index providers (SPY holdings from State Street)

### **Premium Sources to Consider Later:**
- **Analyst Estimates**: Refinitiv/Bloomberg (expensive)
- **Intraday Data**: Premium feeds ($1000+/month)

This data strategy will give you 80-90% of analysis capabilities within your $50-100/month budget while enabling comprehensive multi-agent financial analysis. The key is prioritizing holdings data and options data over premium analyst estimates for the MVP.

---

We need to get the following data: 

- Stocks
- ETFs
- Indexes
- Exchanges

---


### **File: yfinance_client/client.py**

This script is used to fetch and save Yahoo Finance data for a specified ticker.

#### **How it works:**
1. Loads environment variables and imports dependencies.
2. Defines a function `get_ticker_data(ticker)` that pulls detailed information for a given ticker using `yfinance`.
3. When run directly, the script:
   - Prints status messages.
   - Fetches data for a hardcoded example ETF (BLKC).
   - Saves the result as a JSON file in `data/yfinance/blkc.json`.

> This is in active development.


### **Functions:**
- `get_tickers_from_cik_mapping_file(file_path)`  
  Loads and parses ticker list from a mapping JSON file (typically output from sec-edgar-client).
- `get_etfs_from_alphavantage_api()`  
  Downloads and parses the Nasdaq ETF symbol table, returning a deduplicated ETF ticker list.

### **Typical Usage Pattern:**
- Script is executed as `python client.py` after you have an up-to-date `cik_mapping.json`.
- Outputs summary information to console for verification and basic logging.

---

## yfinance_client/source_client.py — Instrument Source Reference Data

This script compiles, standardizes, and saves instrument "source" identifiers for U.S. exchanges and indices using official sources (ISO 10383, AlphaVantage, etc.).

### **Key Steps:**
1. **ISO 10383 Reference Download:**  
   Pulls latest international MIC code registry, extracts the codes for key exchanges (NYSE, NASDAQ, etc.).
2. **ETF and Stock Ticker Download:**  
   Uses AlphaVantage (or other APIs) to get comprehensive lists of U.S. stock and ETF symbols.
3. **Saves Reference Files:**  
   - `exchanges.json`: Maps exchange names to their official MIC codes.
   - `data/yfinance/etf_tickers.json`: List of ETF tickers.
   - `data/yfinance/stock_tickers.json`: List of stock tickers.
4. **Index Constituents:**  
   This script assumes manual tracking of index tickers (e.g., S&P 500 membership) until constituent APIs are automated.

### **Functions:**
- `get_exchanges_from_csv(file_path, exchanges)`  
  Extracts MIC codes from the ISO CSV for given exchange names.
- `get_iso_10383_standard_file()`  
  Downloads (and saves temporarily) the latest ISO 10383 registry for parsing.
- `get_etfs_from_alphavantage_api()`  
  Downloads and serializes ETF list.
- `get_stocks_from_alphavantage_api()`  
  Downloads and serializes stock symbol list.
- `remove_iso_10383_standard_file()`  
  Deletes the temporary ISO registry CSV after extraction.

### **Environment Variables Required:**
- `ISO_SOURCE_URL`: URL for downloading the ISO 10383 registry (often set in `.env` file for flexibility).

### **Typical Usage Pattern:**
- Run as `python source_client.py` — this fetches the latest exchange MICs, ETF, and stock tickers and persists them for downstream tasks.

---

**Note:**  
Both scripts assume you have the required dependencies installed (`pandas`, `requests`, `dotenv`, etc.) and necessary directories (`data/yfinance`, etc.) exist or will be created as needed. They are meant to be rerun regularly to keep your reference and ticker universes fresh, supporting robust and up-to-date financial data pipelines.


