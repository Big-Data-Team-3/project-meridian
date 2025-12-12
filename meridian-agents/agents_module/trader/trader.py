from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
import functools
import time
import json


def create_trader(model: str, memory):
    """
    Create a Trader using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o-mini")
        memory: FinancialSituationMemory instance
    
    Returns:
        A function that takes state and returns updated state
    """
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        # Create system instructions
        system_instructions = f"""You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Do not forget to utilize lessons from past decisions to learn from your mistakes. Here is some reflections from similar situations you traded in and the lessons learned: {past_memory_str}"""

        # Create user message
        user_message = f"""Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.

Proposed Investment Plan: {investment_plan}

Leverage these insights to make an informed and strategic decision."""

        # Create agent and run
        agent = Agent(
            name="Trader",
            instructions=system_instructions,
            model=model,
            tools=[],  # No tools needed for this agent
        )

        try:
            # Use helper to run in isolated thread to avoid event loop conflicts
            result = run_agent_sync(agent, user_message)
            
            # Extract response
            if hasattr(result, 'final_output'):
                response_content = result.final_output
            elif hasattr(result, 'content'):
                response_content = result.content
            elif isinstance(result, str):
                response_content = result
            elif isinstance(result, dict):
                response_content = result.get('final_output') or result.get('content') or str(result)
            else:
                response_content = str(result)

            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=response_content)],
                "trader_investment_plan": response_content,
                "sender": name,
            }
        except Exception as e:
            error_msg = f"Error running trader: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            from langchain_core.messages import AIMessage
            return {
                "messages": [AIMessage(content=error_msg)],
                "trader_investment_plan": error_msg,
                "sender": name,
            }

    return functools.partial(trader_node, name="Trader")
