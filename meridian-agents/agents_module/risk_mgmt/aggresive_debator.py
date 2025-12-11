from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
import time
import json


def create_risky_debator(model: str):
    """
    Create a Risky Debator using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o-mini")
    
    Returns:
        A function that takes state and returns updated state
    """
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # Create system instructions
        system_instructions = """As the Risky Risk Analyst, your role is to actively champion high-reward, high-risk opportunities, emphasizing bold strategies and competitive advantages. When evaluating the trader's decision or plan, focus intently on the potential upside, growth potential, and innovative benefits—even when these come with elevated risk. Use the provided market data and sentiment analysis to strengthen your arguments and challenge the opposing views. Specifically, respond directly to each point made by the conservative and neutral analysts, countering with data-driven rebuttals and persuasive reasoning. Highlight where their caution might miss critical opportunities or where their assumptions may be overly conservative.

Your task is to create a compelling case for the trader's decision by questioning and critiquing the conservative and neutral stances to demonstrate why your high-reward perspective offers the best path forward. Engage actively by addressing any specific concerns raised, refuting the weaknesses in their logic, and asserting the benefits of risk-taking to outpace market norms. Maintain a focus on debating and persuading, not just presenting data. Challenge each counterpoint to underscore why a high-risk approach is optimal. Output conversationally as if you are speaking without any special formatting."""

        # Create user message with context
        user_message = f"""Here is the trader's decision:
{trader_decision}

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Here is the current conversation history: {history}
Here are the last arguments from the conservative analyst: {current_safe_response}
Here are the last arguments from the neutral analyst: {current_neutral_response}

If there are no responses from the other viewpoints, do not hallucinate and just present your point."""

        # Create agent and run
        agent = Agent(
            name="Risky Analyst",
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

            argument = f"Risky Analyst: {response_content}"

            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "risky_history": risky_history + "\n" + argument,
                "safe_history": risk_debate_state.get("safe_history", ""),
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Risky",
                "current_risky_response": argument,
                "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                "current_neutral_response": risk_debate_state.get(
                    "current_neutral_response", ""
                ),
                "count": risk_debate_state["count"] + 1,
            }

            return {
                "risk_debate_state": new_risk_debate_state,
                "sender": "Aggressive Risk Analyst"
            }
        except Exception as e:
            error_msg = f"Error running risky debator: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            argument = f"Risky Analyst: {error_msg}"
            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "risky_history": risky_history + "\n" + argument,
                "safe_history": risk_debate_state.get("safe_history", ""),
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Risky",
                "current_risky_response": argument,
                "current_safe_response": risk_debate_state.get("current_safe_response", ""),
                "current_neutral_response": risk_debate_state.get(
                    "current_neutral_response", ""
                ),
                "count": risk_debate_state["count"] + 1,
            }
            return {
                "risk_debate_state": new_risk_debate_state,
                "sender": "Aggressive Risk Analyst"
            }

    return risky_node
