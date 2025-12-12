import yaml
import importlib
import time
import sys
import os
from pathlib import Path

# Try to load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    # Load from project root or current directory
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try current directory
        load_dotenv()
except ImportError:
    # dotenv not installed, skip
    pass

# Add parent directories to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir.parent.parent))
sys.path.insert(0, str(script_dir))  # Add current directory for local imports

from scorers import score_response
from agents import Runner
from agents_module.utils.runner_helper import run_agent_sync
from agents_module.utils.memory import FinancialSituationMemory
from agents_module.utils.agent_states import InvestDebateState, RiskDebateState
from default_config import DEFAULT_CONFIG

def load_agent_factory(entrypoint):
    """
    Load agent factory function from entrypoint string.
    
    Args:
        entrypoint: String like "agents_module.analysts.market_analyst:create_market_analyst"
    
    Returns:
        Factory function that creates an agent node function
    """
    module_name, function_name = entrypoint.split(":")
    module = importlib.import_module(module_name)
    factory_func = getattr(module, function_name)
    return factory_func

def extract_agent_from_node(node_func):
    """
    Extract the Agent object from a node function by inspecting its closure.
    This is a workaround since factory functions return node functions, not agents directly.
    """
    # Try to get the agent from the closure
    if hasattr(node_func, '__closure__') and node_func.__closure__:
        for cell in node_func.__closure__:
            try:
                obj = cell.cell_contents
                # Check if it's an Agent object (from agents SDK)
                # Agent objects have these attributes
                if hasattr(obj, 'name') and hasattr(obj, 'instructions') and hasattr(obj, 'model'):
                    # Additional check: should have tools attribute
                    if hasattr(obj, 'tools'):
                        return obj
            except (ValueError, AttributeError):
                continue
    
    # If we can't extract it, we'll need to test via the node function
    return None

def create_minimal_state(ticker="AAPL", trade_date="2024-12-19", agent_type="analyst"):
    """
    Create minimal state for different agent types.
    
    Args:
        ticker: Stock ticker symbol
        trade_date: Trade date in YYYY-MM-DD format
        agent_type: Type of agent (analyst, researcher, manager, trader, debator)
    
    Returns:
        Dictionary with minimal state required for the agent
    """
    state = {
        "company_of_interest": ticker,
        "trade_date": trade_date,
        "messages": [],
        # Reports that many agents depend on
        "market_report": f"Sample market analysis for {ticker} showing positive trends.",
        "fundamentals_report": f"Sample fundamentals report for {ticker} showing strong financials.",
        "information_report": f"Sample information report for {ticker} with recent news.",
        "sentiment_report": f"Sample sentiment analysis for {ticker} showing positive sentiment.",
        "news_report": f"Sample news report for {ticker} with recent developments.",
    }
    
    # Add debate states for researchers and managers (but not risk_manager - it needs risk_debate_state)
    if agent_type in ["researcher", "manager"]:
        # For managers that are not risk_manager, they need investment_debate_state
        if agent_type == "manager" and agent_type != "risk_manager":
            state["investment_debate_state"] = {
                "history": "Sample debate history: Bull argues for growth potential, Bear raises concerns about market volatility.",
                "current_response": "",
                "bull_history": "",
                "bear_history": "",
                "count": 0
            }
        else:
            state["investment_debate_state"] = {
                "history": "",
                "current_response": "",
                "bull_history": "",
                "bear_history": "",
                "count": 0
            }
    
    # Add investment debate state for trader
    if agent_type == "trader":
        state["investment_debate_state"] = {
            "history": "Sample debate: Bull case emphasizes growth, Bear case highlights risks.",
            "current_response": "",
            "bull_history": "",
            "bear_history": "",
            "count": 0
        }
    
    # Add risk debate state for risk debators and risk manager
    if agent_type in ["debator", "risk_manager"]:
        # Create as dict since agents access it as state["risk_debate_state"]["history"]
        state["risk_debate_state"] = {
            "history": "Sample risk debate: Risky analyst advocates for aggressive position, Safe analyst recommends caution, Neutral analyst suggests balanced approach.",
            "current_risky_response": "Risky Analyst: High reward potential justifies the risk.",
            "current_safe_response": "Safe Analyst: Conservative approach protects capital.",
            "current_neutral_response": "Neutral Analyst: Moderate risk with balanced returns.",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "count": 0
        }
    
    # Add investment plan for trader, risk debators, and risk_manager
    if agent_type in ["trader", "debator", "risk_manager"]:
        state["investment_plan"] = f"Sample investment plan for {ticker}: Consider BUY with moderate position size. Risk level: Medium. Expected return: 15% over 6 months."
        if agent_type != "risk_manager":  # risk_manager doesn't need trader_investment_plan
            state["trader_investment_plan"] = f"Sample trader plan for {ticker}: BUY recommendation with 5% position size."
    
    return state

def run_test_via_node(node_func, test, ticker="AAPL", trade_date="2024-12-19", agent_type="analyst"):
    """
    Run a test by calling the node function with minimal state.
    Note: The node function will construct its own prompt based on ticker and date,
    but we use the test prompt for documentation/scoring purposes.
    """
    test_prompt = test["prompt"]  # Used for documentation, not execution
    expected = test.get("expected", {})

    # Extract ticker and date from test prompt if possible, otherwise use defaults
    # Try to extract ticker from prompt (look for common patterns)
    import re
    ticker_match = re.search(r'\b([A-Z]{1,5})\b', test_prompt)
    if ticker_match:
        ticker = ticker_match.group(1)
    
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', test_prompt)
    if date_match:
        trade_date = date_match.group(1)

    # Create minimal state for the node function
    state = create_minimal_state(ticker, trade_date, agent_type)

    start = time.time()
    try:
        # Call the node function
        # Some agents (like trader) have different signatures
        import inspect
        sig = inspect.signature(node_func)
        if 'name' in sig.parameters:
            result_state = node_func(state, name="Trader")
        else:
            result_state = node_func(state)
        
        # Extract response from result state
        # Different agents may store results in different keys
        response = ""
        for key in [
            "market_report", "fundamentals_report", "information_report",
            "investment_plan", "trader_investment_plan",
            "final_trade_decision",  # risk_manager uses this
            "judge_decision", "risk_assessment", "final_decision",
            "output", "content", "response"
        ]:
            if key in result_state:
                response = result_state[key]
                if response:  # Only break if we found a non-empty response
                    break
        
        # Check debate states for responses
        if not response and "investment_debate_state" in result_state:
            debate_state = result_state["investment_debate_state"]
            if isinstance(debate_state, dict):
                response = debate_state.get("judge_decision") or debate_state.get("current_response", "")
            elif hasattr(debate_state, "judge_decision"):
                response = debate_state.judge_decision
            elif hasattr(debate_state, "get"):
                response = debate_state.get("judge_decision", "")
        
        if not response and "risk_debate_state" in result_state:
            risk_state = result_state["risk_debate_state"]
            if isinstance(risk_state, dict):
                # For risk_manager: use judge_decision
                # For debators: use current_risky_response, current_safe_response, or current_neutral_response
                # Check sender to determine which response to use
                sender = result_state.get("sender", "").lower()
                if "judge" in sender or "manager" in sender:
                    # This is risk_manager
                    response = risk_state.get("judge_decision") or risk_state.get("risk_assessment") or risk_state.get("final_decision", "")
                else:
                    # This is a debator - get their specific response
                    if "risky" in sender or "aggressive" in sender:
                        response = risk_state.get("current_risky_response", "")
                    elif "safe" in sender or "conservative" in sender:
                        response = risk_state.get("current_safe_response", "")
                    elif "neutral" in sender:
                        response = risk_state.get("current_neutral_response", "")
                    else:
                        # Fallback: try all current responses
                        response = (risk_state.get("current_risky_response") or 
                                   risk_state.get("current_safe_response") or 
                                   risk_state.get("current_neutral_response") or "")
                # Don't use history as it contains our sample text
            elif hasattr(risk_state, "judge_decision"):
                response = risk_state.judge_decision
            elif hasattr(risk_state, "get"):
                response = risk_state.get("judge_decision", "")
        
        # If no report found, try to get from messages
        if not response and "messages" in result_state:
            messages = result_state["messages"]
            if messages:
                # Get the last message (should be the agent's response)
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    response = last_msg.content
                elif isinstance(last_msg, dict):
                    response = last_msg.get("content", str(last_msg))
                else:
                    response = str(last_msg)
        
        if not response:
            # Last resort: try to extract any meaningful text from the state
            response = str(result_state)
            # If it's just a dict representation, try to find any string values
            if response.startswith("{") and "Error" not in response:
                # Look for any report-like keys
                for key, value in result_state.items():
                    if isinstance(value, str) and len(value) > 20:
                        response = value
                        break
            
    except Exception as e:
        error_msg = str(e)
        response = f"Error: {error_msg}"
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in node function: {error_trace}")
        # Don't print full traceback for known state errors - they're expected in some cases
        if "KeyError" in error_msg or "AttributeError" in error_msg:
            print(f"  (State configuration issue - check agent requirements)")
    
    latency = time.time() - start

    score = score_response(response, expected)

    return {
        "id": test["id"],
        "prompt": test_prompt,
        "response": response,
        "score": score,
        "latency": latency
    }

def run_test_direct(agent, test):
    """
    Run a test directly with an Agent object using Runner.
    """
    prompt = test["prompt"]
    expected = test.get("expected", {})

    start = time.time()
    try:
        result = run_agent_sync(agent, prompt)
        
        # Extract response from result
        if hasattr(result, 'final_output'):
            response = result.final_output
        elif hasattr(result, 'content'):
            response = result.content
        elif isinstance(result, str):
            response = result
        else:
            response = str(result)
    except Exception as e:
        response = f"Error: {str(e)}"
    
    latency = time.time() - start

    score = score_response(response, expected)

    return {
        "id": test["id"],
        "prompt": prompt,
        "response": response,
        "score": score,
        "latency": latency
    }

def main():
    # Check for required environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print("❌ ERROR: OPENAI_API_KEY environment variable is not set!")
        print("\nPlease set it before running evals:")
        print("  Option 1: Export as environment variable")
        print("    export OPENAI_API_KEY=your-api-key")
        print("    python run_eval.py")
        print("\n  Option 2: Create a .env file in the project root")
        print("    echo 'OPENAI_API_KEY=your-api-key' > .env")
        print("    python run_eval.py")
        print("\n  Option 3: Set inline")
        print("    OPENAI_API_KEY=your-api-key python run_eval.py")
        sys.exit(1)
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    config_path = script_dir / "eval_config.yaml"
    
    if not config_path.exists():
        print(f"❌ ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path) as f:
        config = yaml.safe_load(f)

    results = []

    # Create test memory instances for agents that need them
    test_config = DEFAULT_CONFIG.copy()
    test_memory = FinancialSituationMemory("test_memory", test_config)
    
    for agent_cfg in config["agents"]:
        print(f"\nTesting agent: {agent_cfg['name']}")
        
        try:
            # Load factory function
            factory_func = load_agent_factory(agent_cfg["entrypoint"])
            
            # Determine agent type for state creation
            agent_name = agent_cfg['name']
            if agent_name == 'risk_manager':
                agent_type = "risk_manager"
            elif 'researcher' in agent_name:
                agent_type = "researcher"
            elif agent_name == 'trader':
                agent_type = "trader"
            elif 'manager' in agent_name:
                agent_type = "manager"  # research_manager
            elif 'debator' in agent_name:
                agent_type = "debator"
            else:
                agent_type = "analyst"
            
            # Create node function with appropriate parameters
            requires_memory = agent_cfg.get("requires_memory", False)
            model = test_config.get("quick_think_llm", "gpt-4o-mini")
            
            if requires_memory:
                # Agents that need memory: bull_researcher, bear_researcher, research_manager, trader, risk_manager
                node_func = factory_func(model=model, memory=test_memory)
            else:
                # Agents that only need model: analysts, debators
                if 'analyst' in agent_name:
                    # Analysts don't need model parameter (use default)
                    node_func = factory_func()
                else:
                    # Debators need model parameter
                    node_func = factory_func(model=model)
            
            # Try to extract agent directly, otherwise use node function
            agent = extract_agent_from_node(node_func)
            
            # Run tests
            for test in agent_cfg.get("tests", []):
                print(f"  Running test: {test['id']}")
                try:
                    if agent:
                        result = run_test_direct(agent, test)
                    else:
                        result = run_test_via_node(node_func, test, agent_type=agent_type)
                    results.append(result)
                    print(f"    Score: {result['score']:.2f}, Latency: {result['latency']:.2f}s")
                except Exception as e:
                    print(f"    Error running test: {str(e)}")
                    results.append({
                        "id": test["id"],
                        "prompt": test.get("prompt", ""),
                        "response": f"Error: {str(e)}",
                        "score": 0.0,
                        "latency": 0.0
                    })

            # Integration tests
            for test in agent_cfg.get("integration_tests", []):
                print(f"  Running integration test: {test['id']}")
                try:
                    if agent:
                        result = run_test_direct(agent, test)
                    else:
                        result = run_test_via_node(node_func, test, agent_type=agent_type)
                    results.append(result)
                    print(f"    Score: {result['score']:.2f}, Latency: {result['latency']:.2f}s")
                except Exception as e:
                    print(f"    Error running test: {str(e)}")
                    results.append({
                        "id": test["id"],
                        "prompt": test.get("prompt", ""),
                        "response": f"Error: {str(e)}",
                        "score": 0.0,
                        "latency": 0.0
                    })
                
        except Exception as e:
            print(f"  Error loading agent {agent_cfg['name']}: {str(e)}")
            import traceback
            traceback.print_exc()

    # Write results as JSON
    import json
    reports_dir = script_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    output_path = reports_dir / "latest.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. Saved to {output_path}")
    print(f"Total tests: {len(results)}")
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    print(f"Average score: {avg_score:.2f}")

if __name__ == "__main__":
    main()
