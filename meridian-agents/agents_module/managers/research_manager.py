from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
import time
import json


def create_research_manager(model: str, memory):
    """
    Create a Research Manager using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o")
        memory: FinancialSituationMemory instance
    
    Returns:
        A function that takes state and returns updated state
    """
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # Create system instructions
        system_instructions = """As the portfolio manager and debate facilitator, your role is to critically evaluate this round of debate and make a definitive decision: align with the bear analyst, the bull analyst, or choose Hold only if it is strongly justified based on the arguments presented.

Summarize the key points from both sides concisely, focusing on the most compelling evidence or reasoning. Your recommendation—Buy, Sell, or Hold—must be clear and actionable. Avoid defaulting to Hold simply because both sides have valid points; commit to a stance grounded in the debate's strongest arguments.

Additionally, develop a detailed investment plan for the trader. This should include:
- Your Recommendation: A decisive stance supported by the most convincing arguments.
- Rationale: An explanation of why these arguments lead to your conclusion.
- Strategic Actions: Concrete steps for implementing the recommendation.

Take into account your past mistakes on similar situations. Use these insights to refine your decision-making and ensure you are learning and improving. Present your analysis conversationally, as if speaking naturally, without special formatting."""

        # Create user message with context
        user_message = f"""Here are your past reflections on mistakes:
{past_memory_str}

Here is the debate:
Debate History:
{history}"""

        # Create agent and run
        agent = Agent(
            name="Research Manager",
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

            new_investment_debate_state = {
                "judge_decision": response_content,
                "history": investment_debate_state.get("history", ""),
                "bear_history": investment_debate_state.get("bear_history", ""),
                "bull_history": investment_debate_state.get("bull_history", ""),
                "current_response": response_content,
                "count": investment_debate_state["count"],
            }

            return {
                "investment_debate_state": new_investment_debate_state,
                "investment_plan": response_content,
                "sender": "Research Manager",
            }
        except Exception as e:
            error_msg = f"Error running research manager: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            new_investment_debate_state = {
                "judge_decision": error_msg,
                "history": investment_debate_state.get("history", ""),
                "bear_history": investment_debate_state.get("bear_history", ""),
                "bull_history": investment_debate_state.get("bull_history", ""),
                "current_response": error_msg,
                "count": investment_debate_state["count"],
            }
            return {
    "investment_debate_state": new_investment_debate_state,
    "investment_plan": error_msg,
    "sender": "Research Manager",  # ← MISSING!
}

    return research_manager_node
