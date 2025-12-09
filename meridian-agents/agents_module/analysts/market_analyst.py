from agents import Agent, Runner
from agents_module.utils.core_stock_tools import get_stock_data
from agents_module.utils.technical_indicators_tools import get_indicators


def create_market_analyst(model: str = "gpt-4o-mini"):
    """
    Create a Market Analyst using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (default: gpt-4o-mini)
    
    Returns:
        A function that takes state and returns updated state with market_report
    """
    # Define tools
    tools = [
        get_stock_data,
        get_indicators,
    ]
    
    # System instructions
    system_instructions = (
        "You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy from the following list. The goal is to choose up to **8 indicators** that provide complementary insights without redundancy. Categories and each category's indicators are:\n\n"
        "Moving Averages:\n"
        "- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.\n"
        "- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.\n"
        "- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.\n\n"
        "MACD Related:\n"
        "- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.\n"
        "- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.\n"
        "- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.\n\n"
        "Momentum Indicators:\n"
        "- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.\n\n"
        "Volatility Indicators:\n"
        "- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.\n"
        "- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.\n"
        "- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.\n"
        "- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.\n\n"
        "Volume-Based Indicators:\n"
        "- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.\n\n"
        "Select indicators that provide diverse and complementary information. Avoid redundancy (e.g., do not select both rsi and stochrsi). Also briefly explain why they are suitable for the given market context. When you tool call, please use the exact name of the indicators provided above as they are defined parameters, otherwise your call will fail. Please make sure to call get_stock_data first to retrieve the CSV that is needed to generate indicators. Then use get_indicators with the specific indicator names. Write a very detailed and nuanced report of the trends you observe. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
        "Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read. "
        "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, "
        "prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
    )
    
    # Create the agent
    agent = Agent(
        name="Market Analyst",
        instructions=system_instructions,
        model=model,
        tools=tools,
    )

    def market_analyst_node(state):
        """
        Node function that uses OpenAI Agents SDK to analyze market data.
        
        Args:
            state: Dictionary containing:
                - company_of_interest: ticker symbol
                - trade_date: current date
                - messages: list of messages (optional)
        
        Returns:
            Dictionary with:
                - messages: updated messages
                - market_report: generated report
        """
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # Get existing messages or create initial message
        messages = state.get("messages", [])
        
        # Calculate date range (30 days back from current date)
        from datetime import datetime, timedelta
        try:
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_dt = current_dt - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
        except:
            start_date = current_date
        
        # Create user message with context
        user_message = (
            f"Analyze the market data for {ticker} as of {current_date}. "
            f"First, retrieve stock price data from {start_date} to {current_date} using get_stock_data. "
            f"Then, use get_indicators to analyze relevant technical indicators. "
            f"Select up to 8 complementary indicators and provide a detailed market analysis report."
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
                "market_report": report,
            }
        except Exception as e:
            error_msg = f"Error running market analyst: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import HumanMessage, AIMessage
            updated_messages = list(messages) if messages else []
            updated_messages.append(HumanMessage(content=user_message))
            updated_messages.append(AIMessage(content=error_msg))
            
            return {
                "messages": updated_messages,
                "market_report": error_msg,
            }

    return market_analyst_node
