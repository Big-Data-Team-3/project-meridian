from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
from agents_module.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)


def create_fundamentals_analyst(model: str = "gpt-4o-mini"):
    """
    Create a Fundamentals Analyst using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        A function that takes state and returns updated state with fundamentals_report
    """
    # Define tools
    tools = [
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    ]
    
    # System instructions
    system_instructions = (
        "You are a researcher tasked with analyzing fundamental information over the past week about a company. "
        "Please write a comprehensive report of the company's fundamental information such as financial documents, "
        "company profile, basic company financials, and company financial history to gain a full view of the company's "
        "fundamental information to inform traders. Make sure to include as much detail as possible. "
        "Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
        "Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read. "
        "Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, "
        "`get_cashflow`, and `get_income_statement` for specific financial statements. "
        "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, "
        "prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
    )
    
    # Create the agent
    agent = Agent(
        name="Fundamentals Analyst",
        instructions=system_instructions,
        model=model,
        tools=tools,
    )
    
    def fundamentals_analyst_node(state):
        """
        Node function that uses OpenAI Agents SDK to analyze fundamentals.
        
        Args:
            state: Dictionary containing:
                - company_of_interest: ticker symbol
                - trade_date: current date
                - messages: list of messages (optional)
        
        Returns:
            Dictionary with:
                - messages: updated messages
                - fundamentals_report: generated report
        """
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # Get existing messages or create initial message
        messages = state.get("messages", [])
        
        # Create user message with context
        user_message = (
            f"Analyze the fundamental information for {ticker} as of {current_date}. "
            f"Use the available tools to gather comprehensive financial data including fundamentals, "
            f"balance sheet, cash flow, and income statement. Provide a detailed analysis report."
        )
        
        # Run the agent using Runner
        try:
            # Use helper to run in isolated thread to avoid event loop conflicts
            result = run_agent_sync(agent, user_message)
            
            # Extract the report from the result
            report = ""
            if hasattr(result, 'final_output'):
                report = result.final_output
            elif hasattr(result, 'content'):
                report = result.content
            elif isinstance(result, str):
                report = result
            elif isinstance(result, dict):
                # Try common keys
                report = result.get('final_output') or result.get('content') or result.get('output', str(result))
            else:
                report = str(result)
            
            # Update messages - add user message and agent response
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=report))
            
            return {
                "messages": updated_messages,
                "fundamentals_report": report,
                "sender": "Fundamentals Analyst",
            }
        except Exception as e:
            error_msg = f"Error running fundamentals analyst: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=error_msg))
            
            return {
                "messages": updated_messages,
                "fundamentals_report": error_msg,
            }

    return fundamentals_analyst_node
