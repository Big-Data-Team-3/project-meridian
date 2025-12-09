from agents import Agent, Runner
from agents_module.utils.news_data_tools import get_news, get_global_news


def create_news_analyst(model: str = "gpt-4o-mini"):
    """
    Create a News Analyst using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        A function that takes state and returns updated state with news_report
    """
    # Define tools
    tools = [
        get_news,
        get_global_news,
    ]
    
    # System instructions
    system_instructions = (
        "You are a news researcher tasked with analyzing recent news and trends over the past week. "
        "Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. "
        "Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, "
        "and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. "
        "Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
        "Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read. "
        "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, "
        "prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
    )
    
    # Create the agent
    agent = Agent(
        name="News Analyst",
        instructions=system_instructions,
        model=model,
        tools=tools,
    )
    
    def news_analyst_node(state):
        """
        Node function that uses OpenAI Agents SDK to analyze news.
        
        Args:
            state: Dictionary containing:
                - company_of_interest: ticker symbol
                - trade_date: current date
                - messages: list of messages (optional)
        
        Returns:
            Dictionary with:
                - messages: updated messages
                - news_report: generated report
        """
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Get existing messages or create initial message
        messages = state.get("messages", [])
        
        # Calculate date range (7 days back from current date)
        from datetime import datetime, timedelta
        try:
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_dt = current_dt - timedelta(days=7)
            start_date = start_dt.strftime("%Y-%m-%d")
        except:
            start_date = current_date
        
        # Create user message with context
        user_message = (
            f"Analyze news and global trends for {ticker} from {start_date} to {current_date}. "
            f"Use get_news to search for company-specific news and get_global_news for broader macroeconomic news. "
            f"Provide a comprehensive report of the current state of the world relevant for trading and macroeconomics."
        )
        
        # Run the agent using Runner
        try:
            # Use Runner.run_sync for synchronous execution
            result = Runner.run_sync(agent, user_message)
            
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
                "news_report": report,
            }
        except Exception as e:
            error_msg = f"Error running news analyst: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=error_msg))
            
            return {
                "messages": updated_messages,
                "news_report": error_msg,
            }

    return news_analyst_node
