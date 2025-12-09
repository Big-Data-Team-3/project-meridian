from agents import Agent, Runner
from agents_module.utils.news_data_tools import get_news


def create_social_media_analyst(model: str = "gpt-4o-mini"):
    """
    Create a Social Media Analyst using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        A function that takes state and returns updated state with sentiment_report
    """
    # Define tools
    tools = [
        get_news,
    ]
    
    # System instructions
    system_instructions = (
        "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, "
        "recent company news, and public sentiment for a specific company over the past week. "
        "You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, "
        "insights, and implications for traders and investors on this company's current state after looking at social media "
        "and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, "
        "and looking at recent company news. Use the get_news(query, start_date, end_date) to search for company-specific "
        "news and social media discussions. Try to look at all sources possible from social media to sentiment to news. "
        "Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
        "Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read. "
        "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, "
        "prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
    )
    
    # Create the agent
    agent = Agent(
        name="Social Media Analyst",
        instructions=system_instructions,
        model=model,
        tools=tools,
    )
    
    def social_media_analyst_node(state):
        """
        Node function that uses OpenAI Agents SDK to analyze social media and sentiment.
        
        Args:
            state: Dictionary containing:
                - company_of_interest: ticker symbol
                - trade_date: current date
                - messages: list of messages (optional)
        
        Returns:
            Dictionary with:
                - messages: updated messages
                - sentiment_report: generated report
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
            f"Analyze social media posts, company news, and public sentiment for {ticker} from {start_date} to {current_date}. "
            f"Use get_news to search for company-specific news and social media discussions. "
            f"Provide a comprehensive report analyzing sentiment, social media trends, and recent company news."
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
                "sentiment_report": report,
            }
        except Exception as e:
            error_msg = f"Error running social media analyst: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=error_msg))
            
            return {
                "messages": updated_messages,
                "sentiment_report": error_msg,
            }

    return social_media_analyst_node
