-- ============================================================================
-- MERIDIAN FINANCIAL INTELLIGENCE PLATFORM
-- Database Schema - PostgreSQL (Third Normal Form - 3NF)
-- ============================================================================
-- 
-- This schema follows Third Normal Form (3NF) principles:
-- 1. First Normal Form (1NF): All attributes are atomic
-- 2. Second Normal Form (2NF): No partial dependencies
-- 3. Third Normal Form (3NF): No transitive dependencies
--
-- Database: meridian_financial_db
-- Version: 1.0.0
-- ============================================================================

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS meridian;
SET search_path TO meridian, public;

-- ============================================================================
-- REFERENCE DATA TABLES (Lookup Tables)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: countries
-- Purpose: Reference table for countries (eliminates transitive dependency)
-- 3NF: Country data is independent, no transitive dependencies
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.countries (
    country_id SERIAL PRIMARY KEY,
    country_code CHAR(2) NOT NULL UNIQUE,  -- ISO 3166-1 alpha-2
    country_name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_countries_code ON meridian.countries(country_code);
CREATE INDEX idx_countries_name ON meridian.countries(country_name);

COMMENT ON TABLE meridian.countries IS 'Reference table for countries to eliminate transitive dependencies';
COMMENT ON COLUMN meridian.countries.country_code IS 'ISO 3166-1 alpha-2 country code';

-- ----------------------------------------------------------------------------
-- Table: exchanges
-- Purpose: Stock exchanges (NYSE, NASDAQ, etc.)
-- 3NF: Exchange data is independent, no transitive dependencies
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.exchanges (
    exchange_id SERIAL PRIMARY KEY,
    exchange_code VARCHAR(10) NOT NULL UNIQUE,  -- NYSE, NASDAQ, etc.
    exchange_name VARCHAR(100) NOT NULL,
    country_id INTEGER NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_exchanges_country 
        FOREIGN KEY (country_id) 
        REFERENCES meridian.countries(country_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE INDEX idx_exchanges_code ON meridian.exchanges(exchange_code);
CREATE INDEX idx_exchanges_country ON meridian.exchanges(country_id);
CREATE INDEX idx_exchanges_active ON meridian.exchanges(is_active);

COMMENT ON TABLE meridian.exchanges IS 'Stock exchanges reference table';
COMMENT ON COLUMN meridian.exchanges.exchange_code IS 'Exchange ticker code (NYSE, NASDAQ, etc.)';

-- ----------------------------------------------------------------------------
-- Table: sectors
-- Purpose: Industry sectors (eliminates transitive dependency from companies)
-- 3NF: Sector data is independent
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.sectors (
    sector_id SERIAL PRIMARY KEY,
    sector_code VARCHAR(20) NOT NULL UNIQUE,  -- TECH, FINANCE, etc.
    sector_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sectors_code ON meridian.sectors(sector_code);
CREATE INDEX idx_sectors_name ON meridian.sectors(sector_name);

COMMENT ON TABLE meridian.sectors IS 'Industry sectors reference table';

-- ----------------------------------------------------------------------------
-- Table: industries
-- Purpose: Industries within sectors (eliminates transitive dependency)
-- 3NF: Industry data is independent, linked to sector
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.industries (
    industry_id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL,
    industry_code VARCHAR(20) NOT NULL,
    industry_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_industries_sector 
        FOREIGN KEY (sector_id) 
        REFERENCES meridian.sectors(sector_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    
    CONSTRAINT uk_industries_code_sector 
        UNIQUE (industry_code, sector_id)
);

CREATE INDEX idx_industries_sector ON meridian.industries(sector_id);
CREATE INDEX idx_industries_code ON meridian.industries(industry_code);

COMMENT ON TABLE meridian.industries IS 'Industries reference table, linked to sectors';

-- ----------------------------------------------------------------------------
-- Table: companies
-- Purpose: Company master data
-- 3NF: All attributes depend only on company_id (primary key)
--      Sector/Industry are foreign keys (no transitive dependency)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.companies (
    company_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    exchange_id INTEGER NOT NULL,
    industry_id INTEGER,
    cik VARCHAR(10),  -- SEC Central Index Key
    company_name VARCHAR(200) NOT NULL,
    legal_name VARCHAR(200),
    website VARCHAR(255),
    headquarters_address TEXT,
    headquarters_city VARCHAR(100),
    headquarters_state VARCHAR(50),
    headquarters_country_id INTEGER,
    phone VARCHAR(20),
    description TEXT,
    founded_year INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_companies_exchange 
        FOREIGN KEY (exchange_id) 
        REFERENCES meridian.exchanges(exchange_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_companies_industry 
        FOREIGN KEY (industry_id) 
        REFERENCES meridian.industries(industry_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_companies_country 
        FOREIGN KEY (headquarters_country_id) 
        REFERENCES meridian.countries(country_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    
    CONSTRAINT uk_companies_symbol_exchange 
        UNIQUE (symbol, exchange_id),
    
    CONSTRAINT ck_companies_cik_format 
        CHECK (cik IS NULL OR (LENGTH(cik) = 10 AND cik ~ '^[0-9]+$'))
);

CREATE INDEX idx_companies_symbol ON meridian.companies(symbol);
CREATE INDEX idx_companies_exchange ON meridian.companies(exchange_id);
CREATE INDEX idx_companies_industry ON meridian.companies(industry_id);
CREATE INDEX idx_companies_cik ON meridian.companies(cik) WHERE cik IS NOT NULL;
CREATE INDEX idx_companies_active ON meridian.companies(is_active);

COMMENT ON TABLE meridian.companies IS 'Company master data table';
COMMENT ON COLUMN meridian.companies.cik IS 'SEC Central Index Key (10 digits)';

-- ----------------------------------------------------------------------------
-- Table: etfs
-- Purpose: ETF master data
-- 3NF: All attributes depend only on etf_id
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.etfs (
    etf_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    exchange_id INTEGER NOT NULL,
    sector_id INTEGER,  -- Primary sector focus
    etf_name VARCHAR(200) NOT NULL,
    description TEXT,
    expense_ratio NUMERIC(6,4),  -- e.g., 0.0300 = 0.03%
    assets_under_mgmt NUMERIC(15,2),  -- In USD
    inception_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_etfs_exchange 
        FOREIGN KEY (exchange_id) 
        REFERENCES meridian.exchanges(exchange_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_etfs_sector 
        FOREIGN KEY (sector_id) 
        REFERENCES meridian.sectors(sector_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    
    CONSTRAINT uk_etfs_symbol_exchange 
        UNIQUE (symbol, exchange_id),
    
    CONSTRAINT ck_etfs_expense_ratio 
        CHECK (expense_ratio IS NULL OR (expense_ratio >= 0 AND expense_ratio <= 1))
);

CREATE INDEX idx_etfs_symbol ON meridian.etfs(symbol);
CREATE INDEX idx_etfs_exchange ON meridian.etfs(exchange_id);
CREATE INDEX idx_etfs_sector ON meridian.etfs(sector_id);
CREATE INDEX idx_etfs_active ON meridian.etfs(is_active);

COMMENT ON TABLE meridian.etfs IS 'ETF master data table';

-- ----------------------------------------------------------------------------
-- Table: indices
-- Purpose: Market indices (S&P 500, NASDAQ, etc.)
-- 3NF: All attributes depend only on index_id
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.indices (
    index_id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    exchange_id INTEGER NOT NULL,
    index_name VARCHAR(100) NOT NULL,
    index_type VARCHAR(50),  -- MARKET_CAP, EQUAL_WEIGHT, etc.
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_indices_exchange 
        FOREIGN KEY (exchange_id) 
        REFERENCES meridian.exchanges(exchange_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE INDEX idx_indices_symbol ON meridian.indices(symbol);
CREATE INDEX idx_indices_exchange ON meridian.indices(exchange_id);
CREATE INDEX idx_indices_active ON meridian.indices(is_active);

COMMENT ON TABLE meridian.indices IS 'Market indices reference table';

-- ----------------------------------------------------------------------------
-- Table: index_constituents
-- Purpose: Many-to-many relationship between indices and companies
-- 3NF: Composite key, no transitive dependencies
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.index_constituents (
    index_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    weight NUMERIC(8,6),  -- Weight in index (0.0 to 1.0)
    as_of_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_index_constituents 
        PRIMARY KEY (index_id, company_id, as_of_date),
    
    CONSTRAINT fk_index_constituents_index 
        FOREIGN KEY (index_id) 
        REFERENCES meridian.indices(index_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_index_constituents_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_index_constituents_weight 
        CHECK (weight IS NULL OR (weight >= 0 AND weight <= 1))
);

CREATE INDEX idx_index_constituents_index ON meridian.index_constituents(index_id);
CREATE INDEX idx_index_constituents_company ON meridian.index_constituents(company_id);
CREATE INDEX idx_index_constituents_date ON meridian.index_constituents(as_of_date);

COMMENT ON TABLE meridian.index_constituents IS 'Many-to-many relationship: indices and their constituent companies';

-- ============================================================================
-- TIME-SERIES DATA TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: stock_prices
-- Purpose: Daily stock price data
-- 3NF: All attributes depend on composite key (date, company_id)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.stock_prices (
    date DATE NOT NULL,
    company_id INTEGER NOT NULL,
    open NUMERIC(12,4) NOT NULL,
    high NUMERIC(12,4) NOT NULL,
    low NUMERIC(12,4) NOT NULL,
    close NUMERIC(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    adjusted_close NUMERIC(12,4),
    dividend_amount NUMERIC(10,4) DEFAULT 0,
    split_coefficient NUMERIC(10,6) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_stock_prices 
        PRIMARY KEY (date, company_id),
    
    CONSTRAINT fk_stock_prices_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_stock_prices_ohlc 
        CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
    
    CONSTRAINT ck_stock_prices_volume 
        CHECK (volume >= 0),
    
    CONSTRAINT ck_stock_prices_split 
        CHECK (split_coefficient > 0)
);

CREATE INDEX idx_stock_prices_company_date ON meridian.stock_prices(company_id, date DESC);
CREATE INDEX idx_stock_prices_date ON meridian.stock_prices(date DESC);
CREATE INDEX idx_stock_prices_company ON meridian.stock_prices(company_id);

COMMENT ON TABLE meridian.stock_prices IS 'Daily stock price OHLCV data';
COMMENT ON COLUMN meridian.stock_prices.adjusted_close IS 'Close price adjusted for splits and dividends';

-- ----------------------------------------------------------------------------
-- Table: etf_prices
-- Purpose: Daily ETF price data
-- 3NF: All attributes depend on composite key (date, etf_id)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.etf_prices (
    date DATE NOT NULL,
    etf_id INTEGER NOT NULL,
    open NUMERIC(12,4) NOT NULL,
    high NUMERIC(12,4) NOT NULL,
    low NUMERIC(12,4) NOT NULL,
    close NUMERIC(12,4) NOT NULL,
    volume BIGINT NOT NULL,
    adjusted_close NUMERIC(12,4),
    dividend_amount NUMERIC(10,4) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_etf_prices 
        PRIMARY KEY (date, etf_id),
    
    CONSTRAINT fk_etf_prices_etf 
        FOREIGN KEY (etf_id) 
        REFERENCES meridian.etfs(etf_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_etf_prices_ohlc 
        CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
    
    CONSTRAINT ck_etf_prices_volume 
        CHECK (volume >= 0)
);

CREATE INDEX idx_etf_prices_etf_date ON meridian.etf_prices(etf_id, date DESC);
CREATE INDEX idx_etf_prices_date ON meridian.etf_prices(date DESC);

COMMENT ON TABLE meridian.etf_prices IS 'Daily ETF price OHLCV data';

-- ----------------------------------------------------------------------------
-- Table: indices_prices
-- Purpose: Daily index price data
-- 3NF: All attributes depend on composite key (date, index_id)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.indices_prices (
    date DATE NOT NULL,
    index_id INTEGER NOT NULL,
    open NUMERIC(12,4) NOT NULL,
    high NUMERIC(12,4) NOT NULL,
    low NUMERIC(12,4) NOT NULL,
    close NUMERIC(12,4) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_indices_prices 
        PRIMARY KEY (date, index_id),
    
    CONSTRAINT fk_indices_prices_index 
        FOREIGN KEY (index_id) 
        REFERENCES meridian.indices(index_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_indices_prices_ohlc 
        CHECK (high >= low AND high >= open AND high >= close AND low <= open AND low <= close),
    
    CONSTRAINT ck_indices_prices_volume 
        CHECK (volume IS NULL OR volume >= 0)
);

CREATE INDEX idx_indices_prices_index_date ON meridian.indices_prices(index_id, date DESC);
CREATE INDEX idx_indices_prices_date ON meridian.indices_prices(date DESC);

COMMENT ON TABLE meridian.indices_prices IS 'Daily index price OHLCV data';

-- ----------------------------------------------------------------------------
-- Table: economic_indicator_types
-- Purpose: Types of economic indicators (eliminates transitive dependency)
-- 3NF: Indicator type data is independent
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.economic_indicator_types (
    indicator_type_id SERIAL PRIMARY KEY,
    indicator_code VARCHAR(50) NOT NULL UNIQUE,  -- FEDFUNDS, GDP, CPI, etc.
    indicator_name VARCHAR(200) NOT NULL,
    category VARCHAR(50),  -- INTEREST_RATE, INFLATION, EMPLOYMENT, etc.
    unit VARCHAR(50),  -- PERCENT, DOLLARS, INDEX, etc.
    frequency VARCHAR(20),  -- DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL
    source VARCHAR(100) DEFAULT 'FRED',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_economic_indicator_types_code ON meridian.economic_indicator_types(indicator_code);
CREATE INDEX idx_economic_indicator_types_category ON meridian.economic_indicator_types(category);

COMMENT ON TABLE meridian.economic_indicator_types IS 'Reference table for economic indicator types (FRED series)';

-- ----------------------------------------------------------------------------
-- Table: economic_indicators
-- Purpose: Economic indicator time-series data (FRED)
-- 3NF: All attributes depend on composite key (date, indicator_type_id)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.economic_indicators (
    date DATE NOT NULL,
    indicator_type_id INTEGER NOT NULL,
    value NUMERIC(20,6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_economic_indicators 
        PRIMARY KEY (date, indicator_type_id),
    
    CONSTRAINT fk_economic_indicators_type 
        FOREIGN KEY (indicator_type_id) 
        REFERENCES meridian.economic_indicator_types(indicator_type_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE INDEX idx_economic_indicators_type_date ON meridian.economic_indicators(indicator_type_id, date DESC);
CREATE INDEX idx_economic_indicators_date ON meridian.economic_indicators(date DESC);

COMMENT ON TABLE meridian.economic_indicators IS 'Economic indicator time-series data from FRED API';

-- ============================================================================
-- FINANCIAL METRICS TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: company_financials
-- Purpose: Quarterly/annual company financial statements
-- 3NF: All attributes depend on composite key (company_id, period_end, statement_type)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.company_financials (
    financial_id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    period_end DATE NOT NULL,
    statement_type VARCHAR(20) NOT NULL,  -- INCOME, BALANCE_SHEET, CASH_FLOW
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,  -- 1-4, NULL for annual
    revenue NUMERIC(15,2),
    net_income NUMERIC(15,2),
    total_assets NUMERIC(15,2),
    total_liabilities NUMERIC(15,2),
    total_equity NUMERIC(15,2),
    operating_cash_flow NUMERIC(15,2),
    free_cash_flow NUMERIC(15,2),
    shares_outstanding BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_company_financials_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT uk_company_financials_unique 
        UNIQUE (company_id, period_end, statement_type),
    
    CONSTRAINT ck_company_financials_quarter 
        CHECK (fiscal_quarter IS NULL OR (fiscal_quarter >= 1 AND fiscal_quarter <= 4)),
    
    CONSTRAINT ck_company_financials_shares 
        CHECK (shares_outstanding IS NULL OR shares_outstanding > 0)
);

CREATE INDEX idx_company_financials_company_period ON meridian.company_financials(company_id, period_end DESC);
CREATE INDEX idx_company_financials_company_year ON meridian.company_financials(company_id, fiscal_year DESC);
CREATE INDEX idx_company_financials_type ON meridian.company_financials(statement_type);

COMMENT ON TABLE meridian.company_financials IS 'Company financial statements (income, balance sheet, cash flow)';

-- ----------------------------------------------------------------------------
-- Table: financial_metrics
-- Purpose: Calculated financial ratios and metrics
-- 3NF: All attributes depend on composite key (company_id, date, metric_type_id)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.financial_metrics (
    company_id INTEGER NOT NULL,
    date DATE NOT NULL,
    metric_type_id INTEGER NOT NULL,
    metric_value NUMERIC(15,6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_financial_metrics 
        PRIMARY KEY (company_id, date, metric_type_id),
    
    CONSTRAINT fk_financial_metrics_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_financial_metrics_type 
        FOREIGN KEY (metric_type_id) 
        REFERENCES meridian.metric_types(metric_type_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE INDEX idx_financial_metrics_company_date ON meridian.financial_metrics(company_id, date DESC);
CREATE INDEX idx_financial_metrics_type ON meridian.financial_metrics(metric_type_id);

COMMENT ON TABLE meridian.financial_metrics IS 'Calculated financial ratios and metrics (P/E, P/B, ROE, etc.)';

-- ----------------------------------------------------------------------------
-- Table: metric_types
-- Purpose: Types of financial metrics (eliminates transitive dependency)
-- 3NF: Metric type data is independent
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.metric_types (
    metric_type_id SERIAL PRIMARY KEY,
    metric_code VARCHAR(50) NOT NULL UNIQUE,  -- PE_RATIO, PB_RATIO, ROE, etc.
    metric_name VARCHAR(100) NOT NULL,
    metric_category VARCHAR(50),  -- VALUATION, PROFITABILITY, LIQUIDITY, etc.
    unit VARCHAR(50),  -- RATIO, PERCENT, DOLLARS, etc.
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metric_types_code ON meridian.metric_types(metric_code);
CREATE INDEX idx_metric_types_category ON meridian.metric_types(metric_category);

COMMENT ON TABLE meridian.metric_types IS 'Reference table for financial metric types';

-- ----------------------------------------------------------------------------
-- Table: feature_store
-- Purpose: ML feature store for model training
-- 3NF: All attributes depend on composite key (company_id, date, feature_name)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.feature_store (
    company_id INTEGER NOT NULL,
    date DATE NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    feature_value NUMERIC(20,8) NOT NULL,
    feature_type VARCHAR(50),  -- TECHNICAL, FUNDAMENTAL, MACRO, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_feature_store 
        PRIMARY KEY (company_id, date, feature_name),
    
    CONSTRAINT fk_feature_store_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE INDEX idx_feature_store_company_date ON meridian.feature_store(company_id, date DESC);
CREATE INDEX idx_feature_store_name ON meridian.feature_store(feature_name);
CREATE INDEX idx_feature_store_type ON meridian.feature_store(feature_type);

COMMENT ON TABLE meridian.feature_store IS 'ML feature store for model training and inference';

-- ============================================================================
-- SEC FILINGS & DOCUMENTS TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: filing_types
-- Purpose: SEC filing types (eliminates transitive dependency)
-- 3NF: Filing type data is independent
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.filing_types (
    filing_type_id SERIAL PRIMARY KEY,
    filing_code VARCHAR(10) NOT NULL UNIQUE,  -- 10-K, 10-Q, 8-K, etc.
    filing_name VARCHAR(100) NOT NULL,
    description TEXT,
    frequency VARCHAR(20),  -- ANNUAL, QUARTERLY, EVENT_DRIVEN
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_filing_types_code ON meridian.filing_types(filing_code);

COMMENT ON TABLE meridian.filing_types IS 'Reference table for SEC filing types';

-- ----------------------------------------------------------------------------
-- Table: sec_filings
-- Purpose: SEC EDGAR filing metadata
-- 3NF: All attributes depend on filing_id (primary key)
--      Filing type is foreign key (no transitive dependency)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.sec_filings (
    filing_id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    filing_type_id INTEGER NOT NULL,
    filing_date DATE NOT NULL,
    period_end DATE,
    accession_number VARCHAR(20) NOT NULL,
    file_url TEXT NOT NULL,
    file_path TEXT,  -- Local storage path
    file_size BIGINT,  -- In bytes
    document_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_sec_filings_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_sec_filings_type 
        FOREIGN KEY (filing_type_id) 
        REFERENCES meridian.filing_types(filing_type_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    
    CONSTRAINT uk_sec_filings_accession 
        UNIQUE (accession_number),
    
    CONSTRAINT ck_sec_filings_dates 
        CHECK (period_end IS NULL OR period_end <= filing_date),
    
    CONSTRAINT ck_sec_filings_size 
        CHECK (file_size IS NULL OR file_size >= 0)
);

CREATE INDEX idx_sec_filings_company_date ON meridian.sec_filings(company_id, filing_date DESC);
CREATE INDEX idx_sec_filings_type ON meridian.sec_filings(filing_type_id);
CREATE INDEX idx_sec_filings_date ON meridian.sec_filings(filing_date DESC);
CREATE INDEX idx_sec_filings_accession ON meridian.sec_filings(accession_number);

COMMENT ON TABLE meridian.sec_filings IS 'SEC EDGAR filing metadata';
COMMENT ON COLUMN meridian.sec_filings.accession_number IS 'SEC accession number (unique identifier)';

-- ----------------------------------------------------------------------------
-- Table: filing_sentiment
-- Purpose: Sentiment analysis results for SEC filings
-- 3NF: All attributes depend on filing_id (primary key)
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.filing_sentiment (
    sentiment_id SERIAL PRIMARY KEY,
    filing_id INTEGER NOT NULL UNIQUE,
    sentiment_score NUMERIC(5,4) NOT NULL,  -- -1.0 to 1.0
    sentiment_label VARCHAR(20) NOT NULL,  -- POSITIVE, NEGATIVE, NEUTRAL
    confidence NUMERIC(4,3) NOT NULL,  -- 0.0 to 1.0
    key_topics TEXT[],  -- Array of key topics
    risk_mentions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_filing_sentiment_filing 
        FOREIGN KEY (filing_id) 
        REFERENCES meridian.sec_filings(filing_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_filing_sentiment_score 
        CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    
    CONSTRAINT ck_filing_sentiment_confidence 
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    CONSTRAINT ck_filing_sentiment_label 
        CHECK (sentiment_label IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL'))
);

CREATE INDEX idx_filing_sentiment_filing ON meridian.filing_sentiment(filing_id);
CREATE INDEX idx_filing_sentiment_score ON meridian.filing_sentiment(sentiment_score);
CREATE INDEX idx_filing_sentiment_label ON meridian.filing_sentiment(sentiment_label);

COMMENT ON TABLE meridian.filing_sentiment IS 'Sentiment analysis results for SEC filings';

-- ============================================================================
-- ANALYTICS & DERIVED DATA TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: portfolio_holdings
-- Purpose: ETF holdings (many-to-many: ETFs and companies)
-- 3NF: Composite key, no transitive dependencies
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.portfolio_holdings (
    etf_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    as_of_date DATE NOT NULL,
    weight NUMERIC(8,6) NOT NULL,  -- Weight in ETF (0.0 to 1.0)
    shares BIGINT,
    market_value NUMERIC(15,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_portfolio_holdings 
        PRIMARY KEY (etf_id, company_id, as_of_date),
    
    CONSTRAINT fk_portfolio_holdings_etf 
        FOREIGN KEY (etf_id) 
        REFERENCES meridian.etfs(etf_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT fk_portfolio_holdings_company 
        FOREIGN KEY (company_id) 
        REFERENCES meridian.companies(company_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    
    CONSTRAINT ck_portfolio_holdings_weight 
        CHECK (weight >= 0 AND weight <= 1),
    
    CONSTRAINT ck_portfolio_holdings_shares 
        CHECK (shares IS NULL OR shares > 0)
);

CREATE INDEX idx_portfolio_holdings_etf_date ON meridian.portfolio_holdings(etf_id, as_of_date DESC);
CREATE INDEX idx_portfolio_holdings_company_date ON meridian.portfolio_holdings(company_id, as_of_date DESC);

COMMENT ON TABLE meridian.portfolio_holdings IS 'ETF holdings: many-to-many relationship between ETFs and companies';

-- ----------------------------------------------------------------------------
-- Table: correlations
-- Purpose: Pre-computed correlation coefficients
-- 3NF: All attributes depend on composite key
-- ----------------------------------------------------------------------------
CREATE TABLE meridian.correlations (
    correlation_id SERIAL PRIMARY KEY,
    symbol1 VARCHAR(10) NOT NULL,
    symbol2 VARCHAR(10) NOT NULL,
    correlation_value NUMERIC(6,5) NOT NULL,  -- -1.0 to 1.0
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    periods INTEGER NOT NULL,  -- Number of data points used
    calculation_method VARCHAR(50) DEFAULT 'PEARSON',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_correlations_unique 
        UNIQUE (symbol1, symbol2, period_start, period_end),
    
    CONSTRAINT ck_correlations_value 
        CHECK (correlation_value >= -1.0 AND correlation_value <= 1.0),
    
    CONSTRAINT ck_correlations_periods 
        CHECK (periods > 0),
    
    CONSTRAINT ck_correlations_dates 
        CHECK (period_end > period_start),
    
    CONSTRAINT ck_correlations_symbols 
        CHECK (symbol1 < symbol2)  -- Prevent duplicate pairs
);

CREATE INDEX idx_correlations_symbol1 ON meridian.correlations(symbol1);
CREATE INDEX idx_correlations_symbol2 ON meridian.correlations(symbol2);
CREATE INDEX idx_correlations_value ON meridian.correlations(correlation_value);

COMMENT ON TABLE meridian.correlations IS 'Pre-computed correlation coefficients between symbols';

-- ============================================================================
-- MATERIALIZED VIEWS (For Performance)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Materialized View: correlation_matrix
-- Purpose: Pre-computed correlation matrix for fast queries
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW meridian.correlation_matrix AS
SELECT 
    c.symbol1,
    c.symbol2,
    c.correlation_value,
    c.period_start,
    c.period_end,
    c.periods,
    c.created_at
FROM meridian.correlations c
WHERE c.period_end >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY c.correlation_value DESC;

CREATE INDEX idx_correlation_matrix_symbol1 ON meridian.correlation_matrix(symbol1);
CREATE INDEX idx_correlation_matrix_symbol2 ON meridian.correlation_matrix(symbol2);

COMMENT ON MATERIALIZED VIEW meridian.correlation_matrix IS 'Pre-computed correlation matrix for recent periods';

-- ----------------------------------------------------------------------------
-- Materialized View: sector_performance
-- Purpose: Aggregated sector-level performance metrics
-- ----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW meridian.sector_performance AS
SELECT 
    s.sector_id,
    s.sector_name,
    sp.date,
    COUNT(DISTINCT sp.company_id) as company_count,
    AVG(sp.close) as avg_price,
    AVG(sp.volume) as avg_volume,
    SUM(sp.volume) as total_volume
FROM meridian.sectors s
JOIN meridian.industries i ON i.sector_id = s.sector_id
JOIN meridian.companies c ON c.industry_id = i.industry_id
JOIN meridian.stock_prices sp ON sp.company_id = c.company_id
WHERE sp.date >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY s.sector_id, s.sector_name, sp.date
ORDER BY s.sector_id, sp.date DESC;

CREATE INDEX idx_sector_performance_sector_date ON meridian.sector_performance(sector_id, date DESC);

COMMENT ON MATERIALIZED VIEW meridian.sector_performance IS 'Aggregated sector-level performance metrics';

-- ============================================================================
-- TRIGGERS (For Data Integrity)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Trigger: Update updated_at timestamp
-- Purpose: Automatically update updated_at column
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION meridian.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON meridian.companies
    FOR EACH ROW
    EXECUTE FUNCTION meridian.update_updated_at_column();

CREATE TRIGGER trg_etfs_updated_at
    BEFORE UPDATE ON meridian.etfs
    FOR EACH ROW
    EXECUTE FUNCTION meridian.update_updated_at_column();

CREATE TRIGGER trg_exchanges_updated_at
    BEFORE UPDATE ON meridian.exchanges
    FOR EACH ROW
    EXECUTE FUNCTION meridian.update_updated_at_column();

-- ============================================================================
-- GRANTS & PERMISSIONS
-- ============================================================================

-- Grant permissions to application user
-- GRANT USAGE ON SCHEMA meridian TO meridian_financial_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA meridian TO meridian_financial_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA meridian TO meridian_financial_user;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================