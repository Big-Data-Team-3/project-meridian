# Meridian Agents System Documentation

## Overview

The Meridian Agents System is a multi-agent financial intelligence platform that uses specialized AI agents to analyze financial data, debate investment strategies, and make trading decisions. The system employs a graph-based workflow where agents collaborate, debate, and reach consensus on investment recommendations.

## Architecture

The system is built using **LangGraph** and follows a **state-based workflow** where agents pass information through a shared state object. The workflow consists of three main phases:

1. **Data Collection & Analysis** - Specialized analysts gather and analyze different types of financial data
2. **Investment Debate** - Bull and Bear researchers debate investment opportunities
3. **Risk Assessment** - Risk analysts evaluate and refine the trading decision

---

## Agent Types

### 1. Data Analysts

These agents collect and analyze specific types of financial data. They run in parallel and each produces a comprehensive report.

#### **Market Analyst** (`market_analyst.py`)
**Purpose:** Analyzes technical market indicators and price trends

**Tools:**
- `get_stock_data(ticker, start_date, end_date)` - Retrieves historical stock price data (OHLCV)
- `get_indicators(ticker, indicators_list)` - Calculates technical indicators

**Available Technical Indicators:**
- **Moving Averages:**
  - `close_50_sma` - 50-day Simple Moving Average
  - `close_200_sma` - 200-day Simple Moving Average
  - `close_10_ema` - 10-day Exponential Moving Average
- **MACD Related:**
  - `macd` - MACD line
  - `macds` - MACD Signal line
  - `macdh` - MACD Histogram
- **Momentum:**
  - `rsi` - Relative Strength Index
- **Volatility:**
  - `boll` - Bollinger Middle Band
  - `boll_ub` - Bollinger Upper Band
  - `boll_lb` - Bollinger Lower Band
  - `atr` - Average True Range
- **Volume:**
  - `vwma` - Volume Weighted Moving Average

**Output:** `market_report` - Detailed technical analysis report with markdown tables

**Data Sources:** yfinance, Alpha Vantage, or local data (configurable)

---

#### **Fundamentals Analyst** (`fundamentals_analyst.py`)
**Purpose:** Analyzes company financial fundamentals and financial statements

**Tools:**
- `get_fundamentals(ticker)` - Retrieves comprehensive company profile and financial overview
- `get_balance_sheet(ticker)` - Gets balance sheet data
- `get_cashflow(ticker)` - Gets cash flow statement data
- `get_income_statement(ticker)` - Gets income statement data

**Output:** `fundamentals_report` - Comprehensive fundamental analysis report with markdown tables

**Data Sources:** Alpha Vantage (default), OpenAI, or local data (configurable)

---

#### **News Analyst** (`news_analyst.py`)
**Purpose:** Analyzes macroeconomic news and global market trends

**Tools:**
- `get_news(query, start_date, end_date)` - Searches for company-specific or targeted news
- `get_global_news(curr_date, look_back_days, limit)` - Retrieves broader macroeconomic news

**Output:** `news_report` - Comprehensive news analysis report with markdown tables

**Data Sources:** Alpha Vantage (default), OpenAI, Google News, or local data (configurable)

---

#### **Social Media Analyst** (`social_media_analyst.py`)
**Purpose:** Analyzes social media sentiment and company-specific news/sentiment

**Tools:**
- `get_news(query, start_date, end_date)` - Searches for company-specific news and social media discussions

**Output:** `sentiment_report` - Comprehensive sentiment analysis report with markdown tables

**Data Sources:** Alpha Vantage, OpenAI, Google News, or local data (configurable)

---

### 2. Research Phase Agents

These agents debate investment opportunities based on the analyst reports.

#### **Bull Researcher** (`bull_researcher.py`)
**Purpose:** Advocates for buying/investing in the stock

**Role:**
- Builds evidence-based case emphasizing growth potential
- Highlights competitive advantages and positive indicators
- Counters bear arguments with data-driven rebuttals
- Uses memory of past similar situations to learn from mistakes

**Inputs:**
- All analyst reports (market, sentiment, news, fundamentals)
- Bear researcher's arguments
- Debate history
- Past memory reflections

**Output:** Updates `investment_debate_state` with bullish arguments

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

#### **Bear Researcher** (`bear_researcher.py`)
**Purpose:** Advocates against investing in the stock

**Role:**
- Presents risks, challenges, and negative indicators
- Highlights competitive weaknesses and threats
- Counters bull arguments with critical analysis
- Uses memory of past similar situations to learn from mistakes

**Inputs:**
- All analyst reports (market, sentiment, news, fundamentals)
- Bull researcher's arguments
- Debate history
- Past memory reflections

**Output:** Updates `investment_debate_state` with bearish arguments

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

#### **Research Manager** (`research_manager.py`)
**Purpose:** Acts as portfolio manager and debate facilitator

**Role:**
- Evaluates the Bull vs Bear debate
- Makes definitive decision: Buy, Sell, or Hold
- Creates detailed investment plan for the trader
- Learns from past mistakes stored in memory

**Inputs:**
- All analyst reports
- Complete debate history
- Past memory reflections from similar situations

**Output:**
- `investment_plan` - Detailed investment plan with recommendation
- `judge_decision` - Final decision with rationale

**LLM:** Deep thinking LLM (o4-mini by default)

**Decision Criteria:**
- Must be clear and actionable (Buy/Sell/Hold)
- Avoids defaulting to Hold unless strongly justified
- Commits to a stance based on strongest arguments

---

### 3. Trading Agent

#### **Trader** (`trader.py`)
**Purpose:** Creates initial trading proposal based on investment plan

**Role:**
- Analyzes the investment plan from Research Manager
- Incorporates insights from all analyst reports
- Makes initial trading decision
- Learns from past trading mistakes

**Inputs:**
- `investment_plan` from Research Manager
- All analyst reports
- Past memory reflections

**Output:**
- `trader_investment_plan` - Initial trading proposal ending with "FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**"

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

### 4. Risk Management Agents

These agents debate the risk profile of the trader's decision.

#### **Risky Analyst** (`aggresive_debator.py`)
**Purpose:** Champions high-reward, high-risk opportunities

**Role:**
- Emphasizes bold strategies and competitive advantages
- Focuses on potential upside and growth potential
- Counters conservative and neutral arguments
- Challenges overly cautious approaches

**Inputs:**
- Trader's investment plan
- All analyst reports
- Conservative and Neutral analyst arguments
- Risk debate history

**Output:** Updates `risk_debate_state` with risky/aggressive arguments

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

#### **Conservative Analyst** (`conservative_debator.py`)
**Purpose:** Prioritizes asset protection and risk mitigation

**Role:**
- Protects assets and minimizes volatility
- Ensures steady, reliable growth
- Critically examines high-risk elements
- Counters risky and neutral arguments

**Inputs:**
- Trader's investment plan
- All analyst reports
- Risky and Neutral analyst arguments
- Risk debate history

**Output:** Updates `risk_debate_state` with conservative arguments

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

#### **Neutral Analyst** (`neutral_debator.py`)
**Purpose:** Provides balanced perspective weighing benefits and risks

**Role:**
- Evaluates both upsides and downsides
- Weighs broader market trends and economic shifts
- Challenges both risky and conservative perspectives
- Advocates for moderate, sustainable strategy

**Inputs:**
- Trader's investment plan
- All analyst reports
- Risky and Conservative analyst arguments
- Risk debate history

**Output:** Updates `risk_debate_state` with neutral/balanced arguments

**LLM:** Quick thinking LLM (gpt-4o-mini by default)

---

#### **Risk Manager** (`risk_manager.py`)
**Purpose:** Final risk assessment and decision refinement

**Role:**
- Evaluates debate between Risky, Neutral, and Safe analysts
- Refines trader's plan based on risk insights
- Makes final recommendation: Buy, Sell, or Hold
- Learns from past mistakes stored in memory

**Inputs:**
- Trader's investment plan
- All analyst reports
- Complete risk debate history
- Past memory reflections

**Output:**
- `final_trade_decision` - Final trading decision with risk-adjusted rationale
- `judge_decision` - Risk manager's decision

**LLM:** Deep thinking LLM (o4-mini by default)

---

## Dataflow & Workflow

### Phase 1: Data Collection (Parallel Analysis)

```
START
  ↓
[Market Analyst] → tools_market → [Market Analyst] → Msg Clear Market
  ↓
[Social Analyst] → tools_social → [Social Analyst] → Msg Clear Social
  ↓
[News Analyst] → tools_news → [News Analyst] → Msg Clear News
  ↓
[Fundamentals Analyst] → tools_fundamentals → [Fundamentals Analyst] → Msg Clear Fundamentals
```

**Flow:**
1. Analysts run sequentially (configurable order)
2. Each analyst can make tool calls to gather data
3. Tool calls are executed via ToolNode
4. Analysts continue until they produce a final report
5. Messages are cleared between analysts for compatibility

**Outputs:**
- `market_report`
- `sentiment_report`
- `news_report`
- `fundamentals_report`

---

### Phase 2: Investment Debate

```
[Bull Researcher] ←→ [Bear Researcher]
         ↓
[Research Manager]
         ↓
[Trader]
```

**Flow:**
1. **Bull Researcher** presents bullish case
2. **Conditional Logic** checks debate count:
   - If < max_debate_rounds: Continue to Bear Researcher
   - If >= max_debate_rounds: Proceed to Research Manager
3. **Bear Researcher** presents bearish case
4. **Conditional Logic** checks debate count:
   - If < max_debate_rounds: Continue to Bull Researcher
   - If >= max_debate_rounds: Proceed to Research Manager
5. **Research Manager** evaluates debate and creates investment plan
6. **Trader** creates initial trading proposal

**Debate Rounds:** Configurable (default: 1 round = 2 total exchanges)

**Outputs:**
- `investment_debate_state` (with history)
- `investment_plan`
- `trader_investment_plan`

---

### Phase 3: Risk Assessment

```
[Trader]
  ↓
[Risky Analyst] → [Safe Analyst] → [Neutral Analyst]
         ↑                              ↓
         └──────────[Risk Judge] ←──────┘
```

**Flow:**
1. **Risky Analyst** presents high-risk, high-reward perspective
2. **Conditional Logic** checks risk debate count:
   - If < max_risk_rounds: Continue to Safe Analyst
   - If >= max_risk_rounds: Proceed to Risk Judge
3. **Safe Analyst** presents conservative perspective
4. **Conditional Logic** checks risk debate count:
   - If < max_risk_rounds: Continue to Neutral Analyst
   - If >= max_risk_rounds: Proceed to Risk Judge
5. **Neutral Analyst** presents balanced perspective
6. **Conditional Logic** checks risk debate count:
   - If < max_risk_rounds: Continue to Risky Analyst (cycle)
   - If >= max_risk_rounds: Proceed to Risk Judge
7. **Risk Judge** makes final decision

**Risk Rounds:** Configurable (default: 1 round = 3 total exchanges)

**Outputs:**
- `risk_debate_state` (with history)
- `final_trade_decision` (final recommendation)

---

## Complete Workflow Diagram

```
START
  ↓
┌─────────────────────────────────────────┐
│  PHASE 1: DATA COLLECTION               │
│  ┌──────────┐  ┌──────────┐            │
│  │  Market  │→ │  Social  │→            │
│  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐            │
│  │   News   │→ │Fundamentals│          │
│  └──────────┘  └──────────┘            │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│  PHASE 2: INVESTMENT DEBATE              │
│  ┌──────────┐      ┌──────────┐        │
│  │   Bull   │ ←──→ │   Bear   │        │
│  └──────────┘      └──────────┘        │
│         ↓              ↓               │
│    ┌──────────────────────┐            │
│    │ Research Manager      │            │
│    └──────────────────────┘            │
│              ↓                          │
│         ┌─────────┐                     │
│         │ Trader  │                     │
│         └─────────┘                     │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│  PHASE 3: RISK ASSESSMENT                │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Risky   │→ │   Safe   │→ │ Neutral │ │
│  └──────────┘  └──────────┘  └─────────┘ │
│       ↑                        ↓         │
│       └──────────┌─────────────┘         │
│                  │ Risk Judge            │
│                  └─────────────┘         │
└─────────────────────────────────────────┘
  ↓
END (Final Trade Decision)
```

---

## State Management

The system uses a shared state object (`AgentState`) that contains:

### Core State Fields:
- `company_of_interest` - Company ticker/name being analyzed
- `trade_date` - Date for the analysis
- `messages` - LangChain message history (for tool calls)

### Analyst Reports:
- `market_report` - Technical analysis report
- `sentiment_report` - Social media sentiment report
- `news_report` - News and macroeconomic report
- `fundamentals_report` - Fundamental analysis report

### Debate States:
- `investment_debate_state` - Contains:
  - `history` - Full debate history
  - `bull_history` - Bull researcher's arguments
  - `bear_history` - Bear researcher's arguments
  - `current_response` - Latest argument
  - `judge_decision` - Research manager's decision
  - `count` - Number of debate rounds

- `risk_debate_state` - Contains:
  - `history` - Full risk debate history
  - `risky_history` - Risky analyst's arguments
  - `safe_history` - Conservative analyst's arguments
  - `neutral_history` - Neutral analyst's arguments
  - `current_risky_response` - Latest risky argument
  - `current_safe_response` - Latest conservative argument
  - `current_neutral_response` - Latest neutral argument
  - `latest_speaker` - Last speaker in debate
  - `judge_decision` - Risk manager's decision
  - `count` - Number of risk debate rounds

### Decisions:
- `investment_plan` - Research manager's investment plan
- `trader_investment_plan` - Trader's initial proposal
- `final_trade_decision` - Final risk-adjusted decision

---

## Memory System

The system uses **FinancialSituationMemory** to learn from past decisions:

### Memory Types:
1. **Bull Memory** - Stores past bullish arguments and outcomes
2. **Bear Memory** - Stores past bearish arguments and outcomes
3. **Trader Memory** - Stores past trading decisions and outcomes
4. **Invest Judge Memory** - Stores research manager's past decisions
5. **Risk Manager Memory** - Stores risk manager's past decisions

### Memory Usage:
- Agents retrieve similar past situations using semantic search
- Past mistakes and lessons are incorporated into current analysis
- Memory is updated after reflection on trading outcomes

---

## Tool System

### Data Source Configuration

The system supports multiple data vendors configured in `default_config.py`:

**Category-level Configuration:**
- `core_stock_apis`: yfinance (default), alpha_vantage, local
- `technical_indicators`: yfinance (default), alpha_vantage, local
- `fundamental_data`: alpha_vantage (default), openai, local
- `news_data`: alpha_vantage (default), openai, google, local

**Tool-level Configuration:**
- Can override category defaults for specific tools

### Available Tools

#### Stock Data Tools (`core_stock_tools.py`):
- `get_stock_data(ticker, start_date, end_date)` - Historical OHLCV data

#### Technical Indicators (`technical_indicators_tools.py`):
- `get_indicators(ticker, indicators_list)` - Calculate technical indicators

#### Fundamental Data (`fundamental_data_tools.py`):
- `get_fundamentals(ticker)` - Company profile and overview
- `get_balance_sheet(ticker)` - Balance sheet data
- `get_cashflow(ticker)` - Cash flow statement
- `get_income_statement(ticker)` - Income statement

#### News & Sentiment (`news_data_tools.py`):
- `get_news(query, start_date, end_date)` - Search news/articles
- `get_global_news(curr_date, look_back_days, limit)` - Global macroeconomic news
- `get_insider_sentiment(ticker)` - Insider trading sentiment
- `get_insider_transactions(ticker)` - Insider transaction data

---

## Configuration

### LLM Configuration

**Providers Supported:**
- OpenAI (default)
- Anthropic
- Google
- Ollama
- OpenRouter

**LLM Types:**
- **Deep Thinking LLM** (default: o4-mini) - Used for:
  - Research Manager
  - Risk Manager
- **Quick Thinking LLM** (default: gpt-4o-mini) - Used for:
  - All Analysts
  - Bull/Bear Researchers
  - Trader
  - Risk Analysts

### Debate Configuration

- `max_debate_rounds` (default: 1) - Investment debate rounds
- `max_risk_discuss_rounds` (default: 1) - Risk debate rounds
- `max_recur_limit` (default: 100) - Maximum graph recursion

---

## API Interface

The system exposes a FastAPI server (`server.py`) with endpoints:

### Health Check
```
GET /health
```
Returns service status and graph initialization state.

### Analyze
```
POST /analyze
Body: {
  "company_name": "AAPL",
  "trade_date": "2024-01-15"
}
```
Runs the complete agent workflow and returns:
- Company name and date
- Final decision (BUY/SELL/HOLD)
- Complete state with all reports and debates

---

## Key Features

1. **Multi-Perspective Analysis**: Four specialized analysts gather different data types
2. **Debate-Based Decision Making**: Bull and Bear researchers debate before decision
3. **Risk Assessment**: Three risk perspectives (Risky, Safe, Neutral) evaluate decisions
4. **Memory & Learning**: Agents learn from past mistakes and similar situations
5. **Configurable Data Sources**: Support for multiple data vendors
6. **Flexible LLM Backend**: Support for multiple LLM providers
7. **State-Based Workflow**: LangGraph manages complex agent interactions
8. **Tool-Based Data Access**: Agents use tools to access real financial data

---

## Example Usage

```python
from graph.trading_graph import TradingAgentsGraph

# Initialize the graph
graph = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
    debug=False
)

# Run analysis
final_state, decision = graph.propagate(
    company_name="AAPL",
    trade_date="2024-01-15"
)

# Access results
print(f"Final Decision: {decision}")
print(f"Market Report: {final_state['market_report']}")
print(f"Investment Plan: {final_state['investment_plan']}")
```

---

## Output Format

The system produces structured outputs:

1. **Analyst Reports**: Markdown-formatted reports with tables
2. **Debate History**: Conversational debate transcripts
3. **Investment Plan**: Detailed plan with recommendation and rationale
4. **Final Decision**: Risk-adjusted trading decision (BUY/SELL/HOLD)

All outputs are stored in the state object and can be logged to JSON files for evaluation and analysis.

---

## Notes

- The system is designed for **analysis only**, not actual trading execution
- All decisions are recommendations based on available data
- Memory system helps agents learn from past mistakes
- The workflow is deterministic but can be configured for different debate lengths
- Tool calls are handled asynchronously through LangGraph's ToolNode

