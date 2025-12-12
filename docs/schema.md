
---

## Reference Data Tables

### 1. `countries`

**Purpose:** Reference table for countries to eliminate transitive dependencies from other tables.

**Key Fields:**
- `country_id` (PK): Unique identifier
- `country_code` (UNIQUE): ISO 3166-1 alpha-2 code (e.g., 'US', 'GB')
- `country_name`: Full country name

**Why Separate Table?**  
Prevents storing country names redundantly in `exchanges` and `companies` tables. Follows 3NF by removing transitive dependency.

**Example Usage:**
SELECT * FROM meridian.countries WHERE country_code = 'US';---

### 2. `exchanges`

**Purpose:** Stock exchanges reference data (NYSE, NASDAQ, etc.)

**Key Fields:**
- `exchange_id` (PK): Unique identifier
- `exchange_code` (UNIQUE): Exchange ticker (e.g., 'NYSE', 'NASDAQ')
- `exchange_name`: Full exchange name
- `country_id` (FK): Links to `countries` table
- `timezone`: Exchange timezone (default: 'America/New_York')

**Relationships:**
- `1:N` with `companies`
- `1:N` with `etfs`
- `1:N` with `indices`

**Example Usage:**
SELECT e.exchange_name, c.country_name
FROM meridian.exchanges e
JOIN meridian.countries c ON e.country_id = c.country_id;---

### 3. `sectors`

**Purpose:** Industry sectors reference table (Technology, Finance, Healthcare, etc.)

**Key Fields:**
- `sector_id` (PK): Unique identifier
- `sector_code` (UNIQUE): Sector code (e.g., 'TECH', 'FINANCE')
- `sector_name`: Full sector name

**Why Separate Table?**  
Eliminates transitive dependency. Instead of storing sector names in `companies` or `etfs`, we reference this table.

**Example Usage:**
SELECT sector_name FROM meridian.sectors WHERE sector_code = 'TECH';---

### 4. `industries`

**Purpose:** Industries within sectors (e.g., "Software" within "Technology")

**Key Fields:**
- `industry_id` (PK): Unique identifier
- `sector_id` (FK): Links to `sectors` table
- `industry_code` (UNIQUE): Industry code
- `industry_name`: Full industry name

**Relationships:**
- `N:1` with `sectors`
- `1:N` with `companies`

**Example Usage:**
SELECT i.industry_name, s.sector_name
FROM meridian.industries i
JOIN meridian.sectors s ON i.sector_id = s.sector_id;---

### 5. `companies`

**Purpose:** Company master data table

**Key Fields:**
- `company_id` (PK): Unique identifier
- `symbol` (UNIQUE with exchange_id): Stock ticker (e.g., 'AAPL')
- `exchange_id` (FK): Links to `exchanges`
- `industry_id` (FK): Links to `industries`
- `cik`: SEC Central Index Key (10 digits)
- `company_name`: Company name
- `is_active`: Whether company is currently active

**Relationships:**
- `N:1` with `exchanges`
- `N:1` with `industries`
- `1:N` with `stock_prices`
- `1:N` with `company_financials`
- `1:N` with `sec_filings`

**Constraints:**
- `uk_companies_symbol_exchange`: Ensures unique symbol per exchange
- `ck_companies_cik_format`: Validates CIK format (10 digits)

**Example Usage:**
SELECT c.symbol, c.company_name, e.exchange_name, i.industry_name
FROM meridian.companies c
JOIN meridian.exchanges e ON c.exchange_id = e.exchange_id
JOIN meridian.industries i ON c.industry_id = i.industry_id
WHERE c.symbol = 'AAPL';---

### 6. `etfs`

**Purpose:** ETF master data table

**Key Fields:**
- `etf_id` (PK): Unique identifier
- `symbol` (UNIQUE with exchange_id): ETF ticker (e.g., 'SPY')
- `exchange_id` (FK): Links to `exchanges`
- `sector_id` (FK): Primary sector focus
- `etf_name`: Full ETF name
- `expense_ratio`: Annual expense ratio (e.g., 0.03 = 0.03%)
- `assets_under_mgmt`: Total assets in USD

**Relationships:**
- `N:1` with `exchanges`
- `N:1` with `sectors`
- `1:N` with `etf_prices`
- `1:N` with `portfolio_holdings`

**Example Usage:**
SELECT etf_name, expense_ratio, assets_under_mgmt
FROM meridian.etfs
WHERE symbol = 'SPY';---

### 7. `indices`

**Purpose:** Market indices reference table (S&P 500, NASDAQ, etc.)

**Key Fields:**
- `index_id` (PK): Unique identifier
- `symbol` (UNIQUE): Index symbol (e.g., 'SPX', 'NDX')
- `exchange_id` (FK): Links to `exchanges`
- `index_name`: Full index name
- `index_type`: Type (e.g., 'MARKET_CAP', 'EQUAL_WEIGHT')

**Relationships:**
- `N:1` with `exchanges`
- `1:N` with `indices_prices`
- `1:N` with `index_constituents`

**Example Usage:**
SELECT index_name FROM meridian.indices WHERE symbol = 'SPX';---

## Time-Series Data Tables

### 8. `stock_prices`

**Purpose:** Daily stock price OHLCV (Open, High, Low, Close, Volume) data

**Key Fields:**
- `date` (PK): Trading date
- `company_id` (PK, FK): Links to `companies`
- `open`, `high`, `low`, `close`: Price data
- `volume`: Trading volume
- `adjusted_close`: Close price adjusted for splits/dividends
- `dividend_amount`: Dividend paid on this date
- `split_coefficient`: Stock split ratio (default: 1.0)

**Primary Key:** `(date, company_id)` - Composite key for time-series data

**Constraints:**
- `ck_stock_prices_ohlc`: Validates OHLC relationships (high >= low, etc.)
- `ck_stock_prices_volume`: Ensures non-negative volume

**Indexes:**
- `idx_stock_prices_company_date`: Optimized for queries by company and date range

**Example Query - Get AAPL data for last 1 year:**ql
SELECT 
    sp.date,
    sp.open,
    sp.high,
    sp.low,
    sp.close,
    sp.volume,
    sp.adjusted_close
FROM meridian.stock_prices sp
JOIN meridian.companies c ON c.company_id = sp.company_id
WHERE c.symbol = 'AAPL'
    AND sp.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY sp.date DESC;**Storage Capacity:**
- Can store unlimited historical data (5+ years supported)
- ~252 trading days/year × 5 years = ~1,260 rows per company
- Efficient for time-range queries with proper indexing

---

### 9. `etf_prices`

**Purpose:** Daily ETF price OHLCV data

**Structure:** Similar to `stock_prices` but for ETFs

**Primary Key:** `(date, etf_id)`

**Example Query:**
SELECT date, close, volume
FROM meridian.etf_prices
WHERE etf_id = (SELECT etf_id FROM meridian.etfs WHERE symbol = 'SPY')
    AND date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY date DESC;---

### 10. `indices_prices`

**Purpose:** Daily index price OHLCV data

**Structure:** Similar to `stock_prices` but for market indices

**Primary Key:** `(date, index_id)`

**Example Query:**
SELECT date, close
FROM meridian.indices_prices
WHERE index_id = (SELECT index_id FROM meridian.indices WHERE symbol = 'SPX')
    AND date >= CURRENT_DATE - INTERVAL '5 years'
ORDER BY date DESC;---

### 11. `economic_indicator_types`

**Purpose:** Reference table for economic indicator types (FRED series)

**Key Fields:**
- `indicator_type_id` (PK): Unique identifier
- `indicator_code` (UNIQUE): FRED series code (e.g., 'FEDFUNDS', 'GDP')
- `indicator_name`: Full indicator name
- `category`: Category (e.g., 'INTEREST_RATE', 'INFLATION')
- `frequency`: Update frequency ('DAILY', 'MONTHLY', 'QUARTERLY')
- `source`: Data source (default: 'FRED')

**Why Separate Table?**  
Eliminates transitive dependency. Instead of storing indicator metadata in each `economic_indicators` row, we reference this table.

---

### 12. `economic_indicators`

**Purpose:** Economic indicator time-series data from FRED API

**Key Fields:**
- `date` (PK): Observation date
- `indicator_type_id` (PK, FK): Links to `economic_indicator_types`
- `value`: Indicator value

**Primary Key:** `(date, indicator_type_id)`

**Example Query:**
SELECT ei.date, eit.indicator_name, ei.value
FROM meridian.economic_indicators ei
JOIN meridian.economic_indicator_types eit ON ei.indicator_type_id = eit.indicator_type_id
WHERE eit.indicator_code = 'FEDFUNDS'
    AND ei.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY ei.date DESC;---

## Financial Metrics Tables

### 13. `company_financials`

**Purpose:** Quarterly/annual company financial statements

**Key Fields:**
- `financial_id` (PK): Unique identifier
- `company_id` (FK): Links to `companies`
- `period_end`: End date of reporting period
- `statement_type`: Type of statement ('INCOME', 'BALANCE_SHEET', 'CASH_FLOW')
- `fiscal_year`: Fiscal year
- `fiscal_quarter`: Quarter (1-4, NULL for annual)
- `revenue`, `net_income`, `total_assets`, etc.: Financial metrics

**Unique Constraint:** `(company_id, period_end, statement_type)` - Prevents duplicate entries

**Example Query:**l
SELECT period_end, revenue, net_income, shares_outstanding
FROM meridian.company_financials
WHERE company_id = (SELECT company_id FROM meridian.companies WHERE symbol = 'AAPL')
    AND statement_type = 'INCOME'
ORDER BY period_end DESC
LIMIT 4;---

### 14. `metric_types`

**Purpose:** Reference table for financial metric types

**Key Fields:**
- `metric_type_id` (PK): Unique identifier
- `metric_code` (UNIQUE): Metric code (e.g., 'PE_RATIO', 'PB_RATIO', 'ROE')
- `metric_name`: Full metric name
- `metric_category`: Category ('VALUATION', 'PROFITABILITY', 'LIQUIDITY')

**Why Separate Table?**  
Eliminates transitive dependency from `financial_metrics` table.

---

### 15. `financial_metrics`

**Purpose:** Calculated financial ratios and metrics over time

**Key Fields:**
- `company_id` (PK, FK): Links to `companies`
- `date` (PK): Calculation date
- `metric_type_id` (PK, FK): Links to `metric_types`
- `metric_value`: Calculated metric value

**Primary Key:** `(company_id, date, metric_type_id)`

**Example Query:**
SELECT 
    fm.date,
    mt.metric_name,
    fm.metric_value
FROM meridian.financial_metrics fm
JOIN meridian.companies c ON c.company_id = fm.company_id
JOIN meridian.metric_types mt ON mt.metric_type_id = fm.metric_type_id
WHERE c.symbol = 'AAPL'
    AND mt.metric_code = 'PE_RATIO'
    AND fm.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY fm.date DESC;---

### 16. `feature_store`

**Purpose:** ML feature store for model training and inference

**Key Fields:**
- `company_id` (PK, FK): Links to `companies`
- `date` (PK): Feature date
- `feature_name` (PK): Feature name
- `feature_value`: Feature value
- `feature_type`: Feature category ('TECHNICAL', 'FUNDAMENTAL', 'MACRO')

**Primary Key:** `(company_id, date, feature_name)`

**Use Case:** Stores pre-computed features for machine learning models (moving averages, technical indicators, etc.)

---

## SEC Filings & Documents Tables

### 17. `filing_types`

**Purpose:** Reference table for SEC filing types

**Key Fields:**
- `filing_type_id` (PK): Unique identifier
- `filing_code` (UNIQUE): Filing code ('10-K', '10-Q', '8-K')
- `filing_name`: Full filing name
- `frequency`: Filing frequency ('ANNUAL', 'QUARTERLY', 'EVENT_DRIVEN')

**Why Separate Table?**  
Eliminates transitive dependency from `sec_filings` table.

---

### 18. `sec_filings`

**Purpose:** SEC EDGAR filing metadata

**Key Fields:**
- `filing_id` (PK): Unique identifier
- `company_id` (FK): Links to `companies`
- `filing_type_id` (FK): Links to `filing_types`
- `filing_date`: Date filing was submitted
- `period_end`: End date of reporting period
- `accession_number` (UNIQUE): SEC accession number
- `file_url`: URL to filing on SEC website
- `file_path`: Local storage path
- `file_size`: File size in bytes

**Relationships:**
- `N:1` with `companies`
- `N:1` with `filing_types`
- `1:1` with `filing_sentiment`

**Example Query:**
SELECT 
    sf.filing_date,
    ft.filing_name,
    sf.period_end,
    sf.file_url
FROM meridian.sec_filings sf
JOIN meridian.companies c ON c.company_id = sf.company_id
JOIN meridian.filing_types ft ON ft.filing_type_id = sf.filing_type_id
WHERE c.symbol = 'AAPL'
    AND ft.filing_code = '10-K'
ORDER BY sf.filing_date DESC;---

### 19. `filing_sentiment`

**Purpose:** Sentiment analysis results for SEC filings

**Key Fields:**
- `sentiment_id` (PK): Unique identifier
- `filing_id` (FK, UNIQUE): Links to `sec_filings` (one-to-one)
- `sentiment_score`: Sentiment score (-1.0 to 1.0)
- `sentiment_label`: Label ('POSITIVE', 'NEGATIVE', 'NEUTRAL')
- `confidence`: Confidence score (0.0 to 1.0)
- `key_topics`: Array of key topics mentioned
- `risk_mentions`: Count of risk factor mentions

**Relationship:** `1:1` with `sec_filings`

**Example Query:**
SELECT 
    sf.filing_date,
    fs.sentiment_score,
    fs.sentiment_label,
    fs.key_topics
FROM meridian.filing_sentiment fs
JOIN meridian.sec_filings sf ON sf.filing_id = fs.filing_id
JOIN meridian.companies c ON c.company_id = sf.company_id
WHERE c.symbol = 'AAPL'
ORDER BY sf.filing_date DESC;
---

## Analytics & Derived Data Tables

### 20. `index_constituents`

**Purpose:** Many-to-many relationship between indices and their constituent companies

**Key Fields:**
- `index_id` (PK, FK): Links to `indices`
- `company_id` (PK, FK): Links to `companies`
- `as_of_date` (PK): Date of composition
- `weight`: Weight in index (0.0 to 1.0)
- `is_active`: Whether company is currently in index

**Primary Key:** `(index_id, company_id, as_of_date)`

**Use Case:** Tracks which companies are in which indices and their weights over time.

**Example Query:**
SELECT 
    c.symbol,
    c.company_name,
    ic.weight,
    ic.as_of_date
FROM meridian.index_constituents ic
JOIN meridian.indices idx ON idx.index_id = ic.index_id
JOIN meridian.companies c ON c.company_id = ic.company_id
WHERE idx.symbol = 'SPX'
    AND ic.as_of_date = (
        SELECT MAX(as_of_date) 
        FROM meridian.index_constituents 
        WHERE index_id = ic.index_id
    )
ORDER BY ic.weight DESC
LIMIT 10;---

### 21. `portfolio_holdings`

**Purpose:** ETF holdings - many-to-many relationship between ETFs and companies

**Key Fields:**
- `etf_id` (PK, FK): Links to `etfs`
- `company_id` (PK, FK): Links to `companies`
- `as_of_date` (PK): Date of holdings snapshot
- `weight`: Weight in ETF portfolio (0.0 to 1.0)
- `shares`: Number of shares held
- `market_value`: Market value of holding

**Primary Key:** `(etf_id, company_id, as_of_date)`

**Use Case:** Tracks what companies each ETF holds and their weights.

**Example Query:**l
SELECT 
    c.symbol,
    c.company_name,
    ph.weight,
    ph.shares,
    ph.market_value
FROM meridian.portfolio_holdings ph
JOIN meridian.etfs e ON e.etf_id = ph.etf_id
JOIN meridian.companies c ON c.company_id = ph.company_id
WHERE e.symbol = 'SPY'
    AND ph.as_of_date = (
        SELECT MAX(as_of_date) 
        FROM meridian.portfolio_holdings 
        WHERE etf_id = ph.etf_id
    )
ORDER BY ph.weight DESC
LIMIT 10;---

### 22. `correlations`

**Purpose:** Pre-computed correlation coefficients between symbols

**Key Fields:**
- `correlation_id` (PK): Unique identifier
- `symbol1`, `symbol2`: Symbols being correlated
- `correlation_value`: Correlation coefficient (-1.0 to 1.0)
- `period_start`, `period_end`: Time period for correlation
- `periods`: Number of data points used
- `calculation_method`: Method used (default: 'PEARSON')

**Unique Constraint:** `(symbol1, symbol2, period_start, period_end)`

**Constraint:** `symbol1 < symbol2` prevents duplicate pairs (e.g., AAPL-MSFT and MSFT-AAPL)

**Example Query:**
SELECT 
    symbol1,
    symbol2,
    correlation_value,
    period_start,
    period_end
FROM meridian.correlations
WHERE (symbol1 = 'AAPL' OR symbol2 = 'AAPL')
    AND period_end >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY ABS(correlation_value) DESC;---

## Materialized Views

### 23. `correlation_matrix`

**Purpose:** Pre-computed correlation matrix for fast queries

**Definition:** Materialized view of recent correlations (last 1 year)

**Refresh:** Should be refreshed daily after data ingestion

**Example Query:**
SELECT * FROM meridian.correlation_matrix
WHERE symbol1 = 'AAPL' OR symbol2 = 'AAPL'
ORDER BY correlation_value DESC;**Refresh Command:**l
REFRESH MATERIALIZED VIEW meridian.correlation_matrix;---

### 24. `sector_performance`

**Purpose:** Aggregated sector-level performance metrics

**Definition:** Aggregates stock prices by sector for the last 1 year

**Fields:**
- `sector_id`, `sector_name`
- `date`
- `company_count`: Number of companies in sector
- `avg_price`, `avg_volume`, `total_volume`

**Example Query:**
SELECT 
    sector_name,
    date,
    company_count,
    avg_price,
    total_volume
FROM meridian.sector_performance
WHERE date >= CURRENT_DATE - INTERVAL '3 months'
ORDER BY sector_name, date DESC;---

## Common Queries

### Get Stock Data for Last 1 Year
ql
SELECT 
    sp.date,
    sp.open,
    sp.high,
    sp.low,
    sp.close,
    sp.volume,
    sp.adjusted_close
FROM meridian.stock_prices sp
JOIN meridian.companies c ON c.company_id = sp.company_id
WHERE c.symbol = 'AAPL'
    AND sp.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY sp.date DESC;### Get Stock Data with Financial Metrics

SELECT 
    sp.date,
    sp.close,
    sp.volume,
    fm.metric_value as pe_ratio
FROM meridian.stock_prices sp
JOIN meridian.companies c ON c.company_id = sp.company_id
LEFT JOIN meridian.financial_metrics fm 
    ON fm.company_id = sp.company_id 
    AND fm.date = sp.date
    AND fm.metric_type_id = (
        SELECT metric_type_id 
        FROM meridian.metric_types 
        WHERE metric_code = 'PE_RATIO'
    )
WHERE c.symbol = 'AAPL'
    AND sp.date >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY sp.date DESC;### Get Sector Performance

SELECT 
    s.sector_name,
    AVG(sp.close) as avg_price,
    SUM(sp.volume) as total_volume,
    COUNT(DISTINCT sp.company_id) as company_count
FROM meridian.sectors s
JOIN meridian.industries i ON i.sector_id = s.sector_id
JOIN meridian.companies c ON c.industry_id = i.industry_id
JOIN meridian.stock_prices sp ON sp.company_id = c.company_id
WHERE sp.date >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY s.sector_id, s.sector_name
ORDER BY avg_price DESC;### Get ETF Holdings

SELECT 
    c.symbol,
    c.company_name,
    ph.weight,
    ph.market_value
FROM meridian.portfolio_holdings ph
JOIN meridian.etfs e ON e.etf_id = ph.etf_id
JOIN meridian.companies c ON c.company_id = ph.company_id
WHERE e.symbol = 'SPY'
    AND ph.as_of_date = (
        SELECT MAX(as_of_date) 
        FROM meridian.portfolio_holdings 
        WHERE etf_id = ph.etf_id
    )
ORDER BY ph.weight DESC;### Get SEC Filings with Sentiment

SELECT 
    sf.filing_date,
    ft.filing_name,
    fs.sentiment_score,
    fs.sentiment_label,
    fs.key_topics
FROM meridian.sec_filings sf
JOIN meridian.companies c ON c.company_id = sf.company_id
JOIN meridian.filing_types ft ON ft.filing_type_id = sf.filing_type_id
LEFT JOIN meridian.filing_sentiment fs ON fs.filing_id = sf.filing_id
WHERE c.symbol = 'AAPL'
    AND ft.filing_code = '10-K'
ORDER BY sf.filing_date DESC;---

## Performance Optimization

### Indexes

The schema includes optimized indexes for common query patterns:

1. **Time-Series Queries:**
   - `idx_stock_prices_company_date`: Optimized for queries by company and date range
   - `idx_etf_prices_etf_date`: Optimized for ETF price queries
   - `idx_economic_indicators_type_date`: Optimized for economic indicator queries

2. **Lookup Queries:**
   - `idx_companies_symbol`: Fast symbol lookups
   - `idx_etfs_symbol`: Fast ETF symbol lookups
   - `idx_indices_symbol`: Fast index symbol lookups

3. **Foreign Key Indexes:**
   - All foreign keys are indexed for efficient joins

### Query Optimization Tips

1. **Use Company ID Directly:**
   -- Faster: Use company_id directly
   SELECT * FROM meridian.stock_prices 
   WHERE company_id = 123 AND date >= CURRENT_DATE - INTERVAL '1 year';
   
   -- Slower: Join with companies table
   SELECT sp.* FROM meridian.stock_prices sp
   JOIN meridian.companies c ON c.company_id = sp.company_id
   WHERE c.symbol = 'AAPL' AND sp.date >= CURRENT_DATE - INTERVAL '1 year';
   2. **Use Date Ranges:**
   - Always filter by date range to limit result set
   - Use `date >= CURRENT_DATE - INTERVAL '1 year'` for recent data

3. **Materialized Views:**
   - Use materialized views for frequently accessed aggregated data
   - Refresh them daily after data ingestion

### Storage Estimates

**Per Company (5 years of data):**
- Stock prices: ~1,260 rows (252 trading days/year × 5 years)
- Financial metrics: ~20 rows (4 quarters/year × 5 years)
- SEC filings: ~25 rows (5 filings/year × 5 years)

**Total for 5,000 companies:**
- Stock prices: ~6.3M rows
- Financial metrics: ~100K rows
- SEC filings: ~125K rows

**Storage Size:** Approximately 2-5 GB for 5 years of data (depending on data types and compression)

---

## Maintenance

### Daily Tasks

1. **Refresh Materialized Views:**
   REFRESH MATERIALIZED VIEW meridian.correlation_matrix;
   REFRESH MATERIALIZED VIEW meridian.sector_performance;
   2. **Data Ingestion:**
   - Run ETL pipeline daily at 2 AM EST
   - Insert new data into time-series tables
   - Update reference data as needed

### Weekly Tasks

1. **Analyze Tables:**
  
   ANALYZE meridian.stock_prices;
   ANALYZE meridian.etf_prices;
   ANALYZE meridian.companies;
   
2. **Check Index Usage:**
 
   SELECT * FROM pg_stat_user_indexes 
   WHERE schemaname = 'meridian';
   ### Monthly Tasks

1. **Vacuum Tables:**
   
   VACUUM ANALYZE meridian.stock_prices;
   VACUUM ANALYZE meridian.etf_prices;
   2. **Review Query Performance:**
   - Check slow query log
   - Optimize frequently used queries

---

## Conclusion

This schema is designed to:
- ✅ Store 5+ years of historical data efficiently
- ✅ Support fast time-series queries
- ✅ Maintain data integrity through 3NF normalization
- ✅ Scale to thousands of companies and ETFs
- ✅ Enable complex analytical queries with proper indexing

For questions or issues, refer to the project documentation or contact the development team.