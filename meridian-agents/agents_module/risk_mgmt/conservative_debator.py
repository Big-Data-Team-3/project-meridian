from agents import Agent, Runner
import time
import json


def create_safe_debator(model: str):
    """
    Create a Safe/Conservative Debator using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o-mini")
    
    Returns:
        A function that takes state and returns updated state
    """
    def safe_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # Create system instructions
        system_instructions = """As the Safe/Conservative Risk Analyst, your primary objective is to protect assets, minimize volatility, and ensure steady, reliable growth. You prioritize stability, security, and risk mitigation, carefully assessing potential losses, economic downturns, and market volatility. When evaluating the trader's decision or plan, critically examine high-risk elements, pointing out where the decision may expose the firm to undue risk and where more cautious alternatives could secure long-term gains.

Your task is to actively counter the arguments of the Risky and Neutral Analysts, highlighting where their views may overlook potential threats or fail to prioritize sustainability. Respond directly to their points, drawing from the data sources to build a convincing case for a low-risk approach adjustment to the trader's decision. Engage by questioning their optimism and emphasizing the potential downsides they may have overlooked. Address each of their counterpoints to showcase why a conservative stance is ultimately the safest path for the firm's assets. Focus on debating and critiquing their arguments to demonstrate the strength of a low-risk strategy over their approaches. Output conversationally as if you are speaking without any special formatting."""

        # Create user message with context
        user_message = f"""Here is the trader's decision:
{trader_decision}

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Here is the current conversation history: {history}
Here is the last response from the risky analyst: {current_risky_response}
Here is the last response from the neutral analyst: {current_neutral_response}

If there are no responses from the other viewpoints, do not hallucinate and just present your point."""

        # Create agent and run
        agent = Agent(
            name="Safe Analyst",
            instructions=system_instructions,
            model=model,
            tools=[],  # No tools needed for this agent
        )

        try:
            result = Runner.run_sync(agent, user_message)
            
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

            argument = f"Safe Analyst: {response_content}"

            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": safe_history + "\n" + argument,
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Safe",
                "current_risky_response": risk_debate_state.get(
                    "current_risky_response", ""
                ),
                "current_safe_response": argument,
                "current_neutral_response": risk_debate_state.get(
                    "current_neutral_response", ""
                ),
                "count": risk_debate_state["count"] + 1,
            }

            return {"risk_debate_state": new_risk_debate_state}
        except Exception as e:
            error_msg = f"Error running safe debator: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            argument = f"Safe Analyst: {error_msg}"
            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": safe_history + "\n" + argument,
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": "Safe",
                "current_risky_response": risk_debate_state.get(
                    "current_risky_response", ""
                ),
                "current_safe_response": argument,
                "current_neutral_response": risk_debate_state.get(
                    "current_neutral_response", ""
                ),
                "count": risk_debate_state["count"] + 1,
            }
            return {"risk_debate_state": new_risk_debate_state}

    return safe_node
