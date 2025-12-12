"""
Initial Agent Registry Population

Populates the agent capability registry with all existing agents.
This module is used to initialize the registry with agent descriptions.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .models import AgentCapability
from .registry import AgentRegistry


def load_schema(agent_id: str) -> Dict[str, Any]:
    """
    Load JSON schema for an agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Dictionary with input_schema and output_schema
    """
    schema_dir = Path(__file__).parent / "schemas"
    schema_file = schema_dir / f"{agent_id}.json"
    
    if schema_file.exists():
        with open(schema_file, 'r') as f:
            return json.load(f)
    else:
        # Return default schema if file doesn't exist
        return {
            "input_schema": {
                "type": "object",
                "required": ["company_of_interest", "trade_date"],
                "properties": {
                    "company_of_interest": {"type": "string"},
                    "trade_date": {"type": "string", "format": "date"}
                }
            },
            "output_schema": {
                "type": "object",
                "required": ["agent_id", "status", "payload"],
                "properties": {
                    "agent_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["success", "failure", "partial"]},
                    "payload": {"type": "object"}
                }
            }
        }


def create_default_registry() -> AgentRegistry:
    """
    Create and populate the default agent registry with all existing agents.
    
    Returns:
        AgentRegistry instance populated with all agents
    """
    registry = AgentRegistry()
    
    # Market Analyst
    market_schema = load_schema("market_analyst")
    registry.register_agent(AgentCapability(
        agent_id="market_analyst",
        agent_name="Market Analyst",
        capabilities=[
            "Technical analysis",
            "Chart pattern recognition",
            "Technical indicator calculation",
            "Price trend analysis",
            "Support/resistance identification"
        ],
        input_schema=market_schema["input_schema"],
        output_schema=market_schema["output_schema"],
        execution_time_estimate=45.0,
        cost_estimate=0.05,
        dependencies=[],
        criticality_default="critical",
        description="Analyzes technical market indicators and price trends using tools like RSI, MACD, Bollinger Bands",
        tools=["get_stock_data", "get_indicators"],
        model_requirements="gpt-4o-mini"
    ))
    
    # Fundamentals Analyst
    fundamentals_schema = load_schema("fundamentals_analyst")
    registry.register_agent(AgentCapability(
        agent_id="fundamentals_analyst",
        agent_name="Fundamentals Analyst",
        capabilities=[
            "Financial statement analysis",
            "Company profile evaluation",
            "Financial ratio calculation",
            "Balance sheet analysis",
            "Income statement analysis",
            "Cash flow analysis"
        ],
        input_schema=fundamentals_schema["input_schema"],
        output_schema=fundamentals_schema["output_schema"],
        execution_time_estimate=60.0,
        cost_estimate=0.08,
        dependencies=[],
        criticality_default="critical",
        description="Evaluates financial statements, key metrics, and company fundamentals",
        tools=["get_fundamentals", "get_balance_sheet", "get_cashflow", "get_income_statement"],
        model_requirements="gpt-4o-mini"
    ))
    
    # Information Analyst
    information_schema = load_schema("information_analyst")
    registry.register_agent(AgentCapability(
        agent_id="information_analyst",
        agent_name="Information Analyst",
        capabilities=[
            "News analysis",
            "Social media sentiment analysis",
            "Global trend analysis",
            "Public perception evaluation",
            "Event detection"
        ],
        input_schema=information_schema["input_schema"],
        output_schema=information_schema["output_schema"],
        execution_time_estimate=50.0,
        cost_estimate=0.06,
        dependencies=[],
        criticality_default="non-critical",
        description="Processes recent news, social media sentiment, and global trends for trading decisions",
        tools=["get_news", "get_global_news"],
        model_requirements="gpt-4o-mini"
    ))
    
    # Bull Researcher
    bull_schema = load_schema("bull_researcher")
    registry.register_agent(AgentCapability(
        agent_id="bull_researcher",
        agent_name="Bull Researcher",
        capabilities=[
            "Bullish investment thesis construction",
            "Growth potential analysis",
            "Competitive advantage identification",
            "Positive indicator synthesis",
            "Bear argument counter-analysis"
        ],
        input_schema=bull_schema["input_schema"],
        output_schema=bull_schema["output_schema"],
        execution_time_estimate=40.0,
        cost_estimate=0.04,
        dependencies=["market_analyst", "fundamentals_analyst", "information_analyst"],
        criticality_default="non-critical",
        description="Generates bullish investment thesis using deep thinking and market data",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Bear Researcher
    bear_schema = load_schema("bull_researcher")  # Same schema structure
    registry.register_agent(AgentCapability(
        agent_id="bear_researcher",
        agent_name="Bear Researcher",
        capabilities=[
            "Bearish investment thesis construction",
            "Risk identification",
            "Downside scenario analysis",
            "Negative indicator synthesis",
            "Bull argument counter-analysis"
        ],
        input_schema=bear_schema["input_schema"],
        output_schema=bear_schema["output_schema"],
        execution_time_estimate=40.0,
        cost_estimate=0.04,
        dependencies=["market_analyst", "fundamentals_analyst", "information_analyst"],
        criticality_default="non-critical",
        description="Generates bearish counter-thesis using deep thinking and market data",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Research Manager
    research_manager_schema = load_schema("research_manager")
    registry.register_agent(AgentCapability(
        agent_id="research_manager",
        agent_name="Research Manager",
        capabilities=[
            "Debate synthesis",
            "Investment plan generation",
            "Consensus building",
            "Decision making",
            "Strategic action planning"
        ],
        input_schema=research_manager_schema["input_schema"],
        output_schema=research_manager_schema["output_schema"],
        execution_time_estimate=50.0,
        cost_estimate=0.10,
        dependencies=["bull_researcher", "bear_researcher"],
        criticality_default="critical",
        description="Synthesizes debate into balanced research report and investment plan",
        tools=[],
        model_requirements="gpt-4o"
    ))
    
    # Trader
    trader_schema = load_schema("trader")
    registry.register_agent(AgentCapability(
        agent_id="trader",
        agent_name="Trader",
        capabilities=[
            "Trading action proposal",
            "Position sizing",
            "Buy/sell/hold recommendation",
            "Investment decision synthesis"
        ],
        input_schema=trader_schema["input_schema"],
        output_schema=trader_schema["output_schema"],
        execution_time_estimate=35.0,
        cost_estimate=0.03,
        dependencies=["research_manager"],
        criticality_default="critical",
        description="Aggregates all analysis and proposes specific trading action with position sizing",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Risky Debator
    risky_schema = load_schema("risky_debator")
    registry.register_agent(AgentCapability(
        agent_id="risky_debator",
        agent_name="Risky Debator",
        capabilities=[
            "Aggressive growth opportunity identification",
            "High-risk/high-reward analysis",
            "Risk tolerance evaluation"
        ],
        input_schema=risky_schema["input_schema"],
        output_schema=risky_schema["output_schema"],
        execution_time_estimate=30.0,
        cost_estimate=0.03,
        dependencies=["trader"],
        criticality_default="non-critical",
        description="Highlights aggressive growth opportunities and risk-taking perspectives",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Safe Debator
    safe_schema = load_schema("safe_debator")
    registry.register_agent(AgentCapability(
        agent_id="safe_debator",
        agent_name="Safe Debator",
        capabilities=[
            "Capital preservation analysis",
            "Conservative risk assessment",
            "Downside protection evaluation"
        ],
        input_schema=safe_schema["input_schema"],
        output_schema=safe_schema["output_schema"],
        execution_time_estimate=30.0,
        cost_estimate=0.03,
        dependencies=["trader"],
        criticality_default="non-critical",
        description="Emphasizes capital preservation and conservative risk management",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Neutral Debator
    neutral_schema = load_schema("neutral_debator")
    registry.register_agent(AgentCapability(
        agent_id="neutral_debator",
        agent_name="Neutral Debator",
        capabilities=[
            "Balanced risk perspective",
            "Moderate risk assessment",
            "Middle-ground analysis"
        ],
        input_schema=neutral_schema["input_schema"],
        output_schema=neutral_schema["output_schema"],
        execution_time_estimate=30.0,
        cost_estimate=0.03,
        dependencies=["trader"],
        criticality_default="non-critical",
        description="Provides balanced risk perspective between aggressive and conservative views",
        tools=[],
        model_requirements="gpt-4o-mini"
    ))
    
    # Risk Manager
    risk_manager_schema = load_schema("risk_manager")
    registry.register_agent(AgentCapability(
        agent_id="risk_manager",
        agent_name="Risk Manager",
        capabilities=[
            "Risk score assignment",
            "Risk synthesis",
            "Final risk assessment",
            "Portfolio risk evaluation"
        ],
        input_schema=risk_manager_schema["input_schema"],
        output_schema=risk_manager_schema["output_schema"],
        execution_time_estimate=45.0,
        cost_estimate=0.08,
        dependencies=["risky_debator", "safe_debator", "neutral_debator"],
        criticality_default="critical",
        description="Synthesizes risk analysis and assigns overall risk score (1-10)",
        tools=[],
        model_requirements="gpt-4o"
    ))
    
    return registry


# Create a singleton instance for easy access
_default_registry: AgentRegistry = None


def get_default_registry() -> AgentRegistry:
    """
    Get or create the default agent registry.
    
    Returns:
        AgentRegistry instance with all agents registered
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry

