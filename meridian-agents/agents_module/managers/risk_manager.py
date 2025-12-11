from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
import time
import json


def create_risk_manager(model: str, memory):
    """
    Create a Risk Manager using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o")
        memory: FinancialSituationMemory instance
    
    Returns:
        A function that takes state and returns updated state
    """
    def risk_manager_node(state) -> dict:
        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["news_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # Create system instructions
        system_instructions = """As the Risk Management Judge and Debate Facilitator, your goal is to evaluate the debate between three risk analysts—Risky, Neutral, and Safe/Conservative—and determine the best course of action for the trader. Your decision must result in a clear recommendation: Buy, Sell, or Hold. Choose Hold only if strongly justified by specific arguments, not as a fallback when all sides seem valid. Strive for clarity and decisiveness.

Guidelines for Decision-Making:
1. **Summarize Key Arguments**: Extract the strongest points from each analyst, focusing on relevance to the context.
2. **Provide Rationale**: Support your recommendation with direct quotes and counterarguments from the debate.
3. **Refine the Trader's Plan**: Start with the trader's original plan and adjust it based on the analysts' insights.
4. **Learn from Past Mistakes**: Use lessons from past reflections to address prior misjudgments and improve the decision you are making now to make sure you don't make a wrong BUY/SELL/HOLD call that loses money.

Deliverables:
- A clear and actionable recommendation: Buy, Sell, or Hold.
- Detailed reasoning anchored in the debate and past reflections.

Focus on actionable insights and continuous improvement. Build on past lessons, critically evaluate all perspectives, and ensure each decision advances better outcomes."""

        # Create user message with context
        user_message = f"""Trader's original plan: {trader_plan}

Past reflections on mistakes:
{past_memory_str}

**Analysts Debate History:**  
{history}"""

        # Create agent and run
        agent = Agent(
            name="Risk Manager",
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

            new_risk_debate_state = {
                "judge_decision": response_content,
                "history": risk_debate_state["history"],
                "risky_history": risk_debate_state["risky_history"],
                "safe_history": risk_debate_state["safe_history"],
                "neutral_history": risk_debate_state["neutral_history"],
                "latest_speaker": "Judge",
                "current_risky_response": risk_debate_state["current_risky_response"],
                "current_safe_response": risk_debate_state["current_safe_response"],
                "current_neutral_response": risk_debate_state["current_neutral_response"],
                "count": risk_debate_state["count"],
            }

            return {
                "risk_debate_state": new_risk_debate_state,
                "final_trade_decision": response_content,
                "sender": "Risk Manager",
            }
        except Exception as e:
            error_msg = f"Error running risk manager: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            new_risk_debate_state = {
                "judge_decision": error_msg,
                "history": risk_debate_state["history"],
                "risky_history": risk_debate_state["risky_history"],
                "safe_history": risk_debate_state["safe_history"],
                "neutral_history": risk_debate_state["neutral_history"],
                "latest_speaker": "Judge",
                "current_risky_response": risk_debate_state["current_risky_response"],
                "current_safe_response": risk_debate_state["current_safe_response"],
                "current_neutral_response": risk_debate_state["current_neutral_response"],
                "count": risk_debate_state["count"],
            }
            return {
                "risk_debate_state": new_risk_debate_state,
                "final_trade_decision": error_msg,
            }

    return risk_manager_node
