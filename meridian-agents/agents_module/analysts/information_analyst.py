from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
from agents_module.utils.news_data_tools import get_news, get_global_news


def create_information_analyst(model: str = "gpt-4o-mini"):
    """
    Create an Information Analyst using OpenAI Agents SDK.
    This agent combines the functionality of both News Analyst and Social Media Analyst.
    
    Args:
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        A function that takes state and returns updated state with information_report
    """
    # Define tools - combining tools from both news and social media analysts
    tools = [
        get_news,
        get_global_news,
    ]
    
    # Combined system instructions covering both news analysis and social media/sentiment analysis
    system_instructions = (
        "You are a comprehensive information analyst tasked with analyzing all available information sources "
        "including news, global trends, social media posts, and public sentiment for trading and investment decisions. "
        "Your objective is to write a comprehensive, detailed report that covers:\n\n"
        "1. **News Analysis**: Analyze recent news and trends over the past week relevant for trading and macroeconomics. "
        "Use get_news(query, start_date, end_date) for company-specific or targeted news searches, "
        "and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news.\n\n"
        "2. **Social Media & Sentiment Analysis**: Analyze social media posts, company news, and public sentiment "
        "for the specific company. Use get_news to search for company-specific news and social media discussions. "
        "Analyze sentiment data of what people feel about the company and look at recent company news from all sources.\n\n"
        "3. **Comprehensive Insights**: Provide detailed and finegrained analysis and insights that may help traders make decisions. "
        "Do not simply state that trends are mixed - provide specific, actionable insights.\n\n"
        "4. **Report Structure**: Organize your report with clear sections covering:\n"
        "   - Global macroeconomic trends and news\n"
        "   - Company-specific news and developments\n"
        "   - Social media sentiment and public perception\n"
        "   - Key insights and implications for traders\n"
        "   - A Markdown table at the end organizing key points in an easy-to-read format\n\n"
        "**Important**: Focus on providing comprehensive information and analysis. Your role is to provide information and insights, "
        "not trading recommendations or decisions."
    )
    
    # Create the agent
    agent = Agent(
        name="Information Analyst",
        instructions=system_instructions,
        model=model,
        tools=tools,
    )
    
    def information_analyst_node(state):
        """
        Node function that uses OpenAI Agents SDK to analyze news, social media, and sentiment.
        
        Args:
            state: Dictionary containing:
                - company_of_interest: ticker symbol
                - trade_date: current date
                - messages: list of messages (optional)
        
        Returns:
            Dictionary with:
                - messages: updated messages
                - information_report: generated comprehensive report
                - news_report: same as information_report (for backward compatibility)
                - sentiment_report: same as information_report (for backward compatibility)
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
        
        # Create comprehensive user message combining both news and social media analysis
        user_message = (
            f"Analyze all available information for {ticker} from {start_date} to {current_date}. "
            f"This includes:\n"
            f"1. News and global trends: Use get_news to search for company-specific news and get_global_news for broader macroeconomic news.\n"
            f"2. Social media and sentiment: Use get_news to search for company-specific news, social media discussions, and sentiment data.\n"
            f"3. Provide a comprehensive report covering:\n"
            f"   - Global macroeconomic trends and news relevant for trading\n"
            f"   - Company-specific news and developments\n"
            f"   - Social media sentiment and public perception\n"
            f"   - Key insights and implications for traders and investors\n"
            f"   - A Markdown table organizing key points at the end\n"
            f"Ensure the analysis is detailed, finegrained, and actionable for trading decisions. "
            f"Focus on providing information and insights, not trading recommendations."
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
                "information_report": report,
                # For backward compatibility with existing code that expects news_report or sentiment_report
                "news_report": report,
                "sentiment_report": report,
                "sender": "Information Analyst",
            }
        except Exception as e:
            error_msg = f"Error running information analyst: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=error_msg))
            
            return {
                "messages": updated_messages,
                "information_report": error_msg,
                # For backward compatibility
                "news_report": error_msg,
                "sentiment_report": error_msg,
            }

    return information_analyst_node

