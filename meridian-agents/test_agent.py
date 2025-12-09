"""
Test script for individual agents
Usage: python test_agent.py --agent fundamentals --ticker AAPL --date 2024-01-15
"""

import argparse
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from agents_module.analysts.fundamentals_analyst import create_fundamentals_analyst
from agents_module.analysts.market_analyst import create_market_analyst
from agents_module.analysts.news_analyst import create_news_analyst
from agents_module.analysts.social_media_analyst import create_social_media_analyst
from agents_module.utils.agent_states import InvestDebateState, RiskDebateState
from default_config import DEFAULT_CONFIG
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from agents_module.utils.memory import FinancialSituationMemory
from agents_module.researchers.bull_researcher import create_bull_researcher
from agents_module.researchers.bear_researcher import create_bear_researcher
from agents_module.managers.research_manager import create_research_manager
from agents_module.trader.trader import create_trader
from agents_module.risk_mgmt.aggresive_debator import create_risky_debator
from agents_module.risk_mgmt.conservative_debator import create_safe_debator
from agents_module.risk_mgmt.neutral_debator import create_neutral_debator
from agents_module.managers.risk_manager import create_risk_manager

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Warning: OPENAI_API_KEY not set")
    exit(1)

def create_test_state(ticker: str, date: str, include_sample_reports: bool = False) -> dict:
    """Create a minimal test state for an agent"""
    state = {
        "messages": [HumanMessage(content=f"Analyze {ticker}")],
        "company_of_interest": ticker,
        "trade_date": date,
        "investment_debate_state": InvestDebateState({
            "history": "",
            "current_response": "",
            "count": 0
        }),
        "risk_debate_state": RiskDebateState({
            "history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0
        }),
        "market_report": "",
        "fundamentals_report": "",
        "sentiment_report": "",
        "news_report": "",
        "investment_plan": "",
        "trader_investment_plan": "",
    }
    
    # Add sample reports if needed for testing dependent agents
    if include_sample_reports:
        state.update({
            "market_report": f"Sample market report for {ticker}: Stock shows positive momentum with strong technical indicators.",
            "fundamentals_report": f"Sample fundamentals report for {ticker}: Company has solid financials with growing revenue.",
            "sentiment_report": f"Sample sentiment report for {ticker}: Social media sentiment is generally positive.",
            "news_report": f"Sample news report for {ticker}: Recent news indicates favorable market conditions.",
            "investment_plan": f"Sample investment plan for {ticker}: Consider buying with moderate position size.",
        })
    
    return state

def test_fundamentals_analyst(ticker: str, date: str):
    """Test Fundamentals Analyst agent using OpenAI Agents SDK"""
    print(f"🧪 Testing Fundamentals Analyst (OpenAI Agents SDK) for {ticker} on {date}")
    print("=" * 60)
    
    agent_func = create_fundamentals_analyst(model="gpt-4o-mini")
    state = create_test_state(ticker, date)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        report = final_state.get("fundamentals_report", "")
        messages = final_state.get("messages", [])
        
        if not report:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    report = msg.content
                    break
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Fundamentals Report:")
        print("=" * 60)
        print(report[:1000] if report else "No report generated")
        if report and len(report) > 1000:
            print(f"\n... (truncated, total length: {len(report)} characters)")
        print("=" * 60)
        print(f"\n📝 Total messages: {len(messages)}")
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_market_analyst(ticker: str, date: str):
    """Test Market Analyst agent using OpenAI Agents SDK"""
    print(f"🧪 Testing Market Analyst (OpenAI Agents SDK) for {ticker} on {date}")
    print("=" * 60)
    
    agent_func = create_market_analyst(model="gpt-4o-mini")
    state = create_test_state(ticker, date)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        report = final_state.get("market_report", "")
        messages = final_state.get("messages", [])
        
        if not report:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    report = msg.content
                    break
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Market Report Preview:")
        print("=" * 60)
        print(report[:1000] if report else "No report generated")
        if report and len(report) > 1000:
            print(f"\n... (truncated, total length: {len(report)} characters)")
        print("=" * 60)
        print(f"\n📝 Total messages: {len(messages)}")
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_news_analyst(ticker: str, date: str):
    """Test News Analyst agent using OpenAI Agents SDK"""
    print(f"🧪 Testing News Analyst (OpenAI Agents SDK) for {ticker} on {date}")
    print("=" * 60)
    
    agent_func = create_news_analyst(model="gpt-4o-mini")
    state = create_test_state(ticker, date)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        report = final_state.get("news_report", "")
        messages = final_state.get("messages", [])
        
        if not report:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    report = msg.content
                    break
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 News Report Preview:")
        print("=" * 60)
        print(report[:1000] if report else "No report generated")
        if report and len(report) > 1000:
            print(f"\n... (truncated, total length: {len(report)} characters)")
        print("=" * 60)
        print(f"\n📝 Total messages: {len(messages)}")
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_social_media_analyst(ticker: str, date: str):
    """Test Social Media Analyst agent using OpenAI Agents SDK"""
    print(f"🧪 Testing Social Media Analyst (OpenAI Agents SDK) for {ticker} on {date}")
    print("=" * 60)
    
    agent_func = create_social_media_analyst(model="gpt-4o-mini")
    state = create_test_state(ticker, date)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        report = final_state.get("sentiment_report", "")
        messages = final_state.get("messages", [])
        
        if not report:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    report = msg.content
                    break
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Sentiment Report Preview:")
        print("=" * 60)
        print(report[:1000] if report else "No report generated")
        if report and len(report) > 1000:
            print(f"\n... (truncated, total length: {len(report)} characters)")
        print("=" * 60)
        print(f"\n📝 Total messages: {len(messages)}")
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

# Test functions for agents that use LLM directly (LangChain, not OpenAI Agents SDK)
def test_bull_researcher(ticker: str, date: str):
    """Test Bull Researcher agent"""
    print(f"🧪 Testing Bull Researcher for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = FinancialSituationMemory("bull_memory", DEFAULT_CONFIG)
    agent_func = create_bull_researcher(llm, memory)
    
    # Create state with sample reports (bull researcher needs reports from analysts)
    state = create_test_state(ticker, date, include_sample_reports=True)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        debate_state = final_state.get("investment_debate_state", {})
        argument = debate_state.get("current_response", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Bull Argument:")
        print("=" * 60)
        print(argument[:1000] if argument else "No argument generated")
        if argument and len(argument) > 1000:
            print(f"\n... (truncated, total length: {len(argument)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_bear_researcher(ticker: str, date: str):
    """Test Bear Researcher agent"""
    print(f"🧪 Testing Bear Researcher for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = FinancialSituationMemory("bear_memory", DEFAULT_CONFIG)
    agent_func = create_bear_researcher(llm, memory)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        debate_state = final_state.get("investment_debate_state", {})
        argument = debate_state.get("current_response", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Bear Argument:")
        print("=" * 60)
        print(argument[:1000] if argument else "No argument generated")
        if argument and len(argument) > 1000:
            print(f"\n... (truncated, total length: {len(argument)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_research_manager(ticker: str, date: str):
    """Test Research Manager agent"""
    print(f"🧪 Testing Research Manager for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = FinancialSituationMemory("invest_judge_memory", DEFAULT_CONFIG)
    agent_func = create_research_manager(llm, memory)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    
    # Add some debate history for the research manager to evaluate
    state["investment_debate_state"]["history"] = "Bull Analyst: This stock has strong growth potential.\nBear Analyst: There are significant risks to consider."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        investment_plan = final_state.get("investment_plan", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Investment Plan:")
        print("=" * 60)
        print(investment_plan[:1000] if investment_plan else "No plan generated")
        if investment_plan and len(investment_plan) > 1000:
            print(f"\n... (truncated, total length: {len(investment_plan)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_trader(ticker: str, date: str):
    """Test Trader agent"""
    print(f"🧪 Testing Trader for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = FinancialSituationMemory("trader_memory", DEFAULT_CONFIG)
    agent_func = create_trader(llm, memory)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    state["investment_plan"] = "Sample investment plan: Buy with moderate position size."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        trader_plan = final_state.get("trader_investment_plan", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Trader Decision:")
        print("=" * 60)
        print(trader_plan[:1000] if trader_plan else "No decision generated")
        if trader_plan and len(trader_plan) > 1000:
            print(f"\n... (truncated, total length: {len(trader_plan)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_risky_debator(ticker: str, date: str):
    """Test Risky Debator agent"""
    print(f"🧪 Testing Risky Debator for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent_func = create_risky_debator(llm)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    state["trader_investment_plan"] = "Sample trader decision: Buy with high risk tolerance."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        debate_state = final_state.get("risk_debate_state", {})
        argument = debate_state.get("current_risky_response", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Risky Argument:")
        print("=" * 60)
        print(argument[:1000] if argument else "No argument generated")
        if argument and len(argument) > 1000:
            print(f"\n... (truncated, total length: {len(argument)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_safe_debator(ticker: str, date: str):
    """Test Safe Debator agent"""
    print(f"🧪 Testing Safe Debator for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent_func = create_safe_debator(llm)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    state["trader_investment_plan"] = "Sample trader decision: Buy with moderate risk."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        debate_state = final_state.get("risk_debate_state", {})
        argument = debate_state.get("current_safe_response", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Safe Argument:")
        print("=" * 60)
        print(argument[:1000] if argument else "No argument generated")
        if argument and len(argument) > 1000:
            print(f"\n... (truncated, total length: {len(argument)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_neutral_debator(ticker: str, date: str):
    """Test Neutral Debator agent"""
    print(f"🧪 Testing Neutral Debator for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent_func = create_neutral_debator(llm)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    state["trader_investment_plan"] = "Sample trader decision: Hold with balanced approach."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        debate_state = final_state.get("risk_debate_state", {})
        argument = debate_state.get("current_neutral_response", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Neutral Argument:")
        print("=" * 60)
        print(argument[:1000] if argument else "No argument generated")
        if argument and len(argument) > 1000:
            print(f"\n... (truncated, total length: {len(argument)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_risk_manager(ticker: str, date: str):
    """Test Risk Manager agent"""
    print(f"🧪 Testing Risk Manager for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = FinancialSituationMemory("risk_manager_memory", DEFAULT_CONFIG)
    agent_func = create_risk_manager(llm, memory)
    
    state = create_test_state(ticker, date, include_sample_reports=True)
    state["investment_plan"] = "Sample investment plan: Buy with moderate position."
    
    # Add some risk debate history
    state["risk_debate_state"]["history"] = "Risky Analyst: High risk, high reward opportunity.\nSafe Analyst: Too risky, recommend caution.\nNeutral Analyst: Balanced approach recommended."
    
    print(f"📊 Running agent for {ticker}...")
    print(f"📅 Trade date: {date}")
    print()
    
    try:
        final_state = agent_func(state)
        decision = final_state.get("final_trade_decision", "")
        
        print("\n✅ Agent executed successfully!")
        print(f"\n📊 Final Trade Decision:")
        print("=" * 60)
        print(decision[:1000] if decision else "No decision generated")
        if decision and len(decision) > 1000:
            print(f"\n... (truncated, total length: {len(decision)} characters)")
        print("=" * 60)
        
        return final_state
    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test individual agents")
    parser.add_argument("--agent", required=True, 
                       choices=["market", "fundamentals", "news", "social", 
                               "bull", "bear", "research_manager", "trader",
                               "risky", "safe", "neutral", "risk_manager"],
                       help="Agent to test")
    parser.add_argument("--ticker", default="AAPL", help="Stock ticker")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), 
                       help="Trade date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Run the appropriate test
    if args.agent == "fundamentals":
        test_fundamentals_analyst(args.ticker, args.date)
    elif args.agent == "market":
        test_market_analyst(args.ticker, args.date)
    elif args.agent == "news":
        test_news_analyst(args.ticker, args.date)
    elif args.agent == "social":
        test_social_media_analyst(args.ticker, args.date)
    elif args.agent == "bull":
        test_bull_researcher(args.ticker, args.date)
    elif args.agent == "bear":
        test_bear_researcher(args.ticker, args.date)
    elif args.agent == "research_manager":
        test_research_manager(args.ticker, args.date)
    elif args.agent == "trader":
        test_trader(args.ticker, args.date)
    elif args.agent == "risky":
        test_risky_debator(args.ticker, args.date)
    elif args.agent == "safe":
        test_safe_debator(args.ticker, args.date)
    elif args.agent == "neutral":
        test_neutral_debator(args.ticker, args.date)
    elif args.agent == "risk_manager":
        test_risk_manager(args.ticker, args.date)
    else:
        print(f"❌ Agent '{args.agent}' test not implemented yet")