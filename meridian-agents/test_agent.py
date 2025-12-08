"""
Test script for individual agents
Usage: python test_agent.py --agent market --ticker AAPL --date 2024-01-15
"""

import argparse
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from agents_module.analysts.market_analyst import create_market_analyst
from agents_module.analysts.fundamentals_analyst import create_fundamentals_analyst
from agents_module.analysts.news_analyst import create_news_analyst
from agents_module.analysts.social_media_analyst import create_social_media_analyst
from agents_module.researchers.bull_researcher import create_bull_researcher
from agents_module.researchers.bear_researcher import create_bear_researcher
from agents_module.managers.research_manager import create_research_manager
from agents_module.trader.trader import create_trader
from agents_module.risk_mgmt.aggresive_debator import create_risky_debator
from agents_module.risk_mgmt.conservative_debator import create_safe_debator
from agents_module.risk_mgmt.neutral_debator import create_neutral_debator
from agents_module.managers.risk_manager import create_risk_manager
from agents_module.utils.agent_states import AgentState, InvestDebateState, RiskDebateState
from agents_module.utils.memory import FinancialSituationMemory
from agents_module.utils.agent_utils import (
    get_stock_data, get_indicators, get_fundamentals, 
    get_balance_sheet, get_cashflow, get_income_statement,
    get_news, get_global_news
)
from default_config import DEFAULT_CONFIG
import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  Warning: OPENAI_API_KEY not set")
    exit(1)

def create_test_state(ticker: str, date: str) -> dict:
    """Create a minimal test state for an agent"""
    return {
        "messages": [HumanMessage(content=ticker)],
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

def run_agent_with_tools(agent_func, state, tools, max_iterations=5):
    """Run an agent, executing tools until it produces a final report"""
    from langchain_core.messages import ToolMessage
    
    for iteration in range(max_iterations):
        # Run the agent
        result = agent_func(state)
        
        # Update state with agent result
        state.update(result)
        messages = state.get("messages", [])
        
        # Get the last message
        last_message = messages[-1] if messages else None
        
        # Check if agent made tool calls
        if last_message and hasattr(last_message, 'tool_calls') and len(last_message.tool_calls) > 0:
            print(f"  🔧 Iteration {iteration + 1}: Agent made {len(last_message.tool_calls)} tool call(s)")
            
            # Create a tool map for easy lookup
            tool_map = {tool.name: tool for tool in tools}
            
            # Execute each tool call manually
            tool_messages = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                
                if tool_name in tool_map:
                    try:
                        print(f"    📞 Calling tool: {tool_name} with args: {tool_args}")
                        tool_result = tool_map[tool_name].invoke(tool_args)
                        tool_messages.append(
                            ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call.get("id", f"call_{tool_name}")
                            )
                        )
                        print(f"    ✅ Tool {tool_name} executed successfully")
                    except Exception as e:
                        print(f"    ❌ Tool {tool_name} failed: {e}")
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_call.get("id", f"call_{tool_name}")
                            )
                        )
                else:
                    print(f"    ⚠️  Tool {tool_name} not found in available tools")
            
            # Add tool results to messages
            state["messages"].extend(tool_messages)
            
            # Continue loop to let agent process tool results
            continue
        else:
            # No more tool calls, agent has final answer
            print(f"  ✅ Iteration {iteration + 1}: Agent produced final report")
            break
    
    return state

def test_fundamentals_analyst(ticker: str, date: str):
    """Test Fundamentals Analyst agent"""
    print(f"🧪 Testing Fundamentals Analyst for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_fundamentals_analyst(llm)
    state = create_test_state(ticker, date)
    
    # Tools for fundamentals analyst
    tools = [
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    ]
    
    # Run agent with tool execution
    final_state = run_agent_with_tools(agent, state, tools)
    
    # Extract report from final message
    messages = final_state.get("messages", [])
    report = ""
    
    # Look for the final AI message with content
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
            report = msg.content
            break
    
    # Also check the fundamentals_report field
    if not report:
        report = final_state.get("fundamentals_report", "")
    
    print("\n✅ Agent executed successfully!")
    print(f"\n📊 Fundamentals Report:")
    print(report if report else "No report generated")
    print("\n" + "=" * 60)
    
    return final_state

def test_market_analyst(ticker: str, date: str):
    """Test Market Analyst agent"""
    print(f"🧪 Testing Market Analyst for {ticker} on {date}")
    print("=" * 60)
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_market_analyst(llm)
    state = create_test_state(ticker, date)
    
    # Tools for market analyst
    tools = [
        get_stock_data,
        get_indicators,
    ]
    
    # Run agent with tool execution
    final_state = run_agent_with_tools(agent, state, tools)
    
    # Extract report
    messages = final_state.get("messages", [])
    report = ""
    
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
            report = msg.content
            break
    
    if not report:
        report = final_state.get("market_report", "")
    
    print("\n✅ Agent executed successfully!")
    print(f"\n📊 Market Report Preview:")
    print(report[:500] if report else "No report generated")
    print("\n" + "=" * 60)
    
    return final_state

# Add similar functions for other agents...

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
    if args.agent == "market":
        test_market_analyst(args.ticker, args.date)
    elif args.agent == "fundamentals":
        test_fundamentals_analyst(args.ticker, args.date)
    # Add more elif blocks for other agents...
    else:
        print(f"❌ Agent '{args.agent}' test not implemented yet")