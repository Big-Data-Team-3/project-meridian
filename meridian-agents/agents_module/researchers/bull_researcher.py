from agents import Agent, Runner
from agents_module.utils.runner_helper import run_agent_sync
import time
import json


def create_bull_researcher(model: str, memory):
    """
    Create a Bull Researcher using OpenAI Agents SDK.
    
    Args:
        model: OpenAI model to use (e.g., "gpt-4o-mini")
        memory: FinancialSituationMemory instance
    
    Returns:
        A function that takes state and returns updated state
    """
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # Create system instructions
        system_instructions = """You are a Bull Analyst advocating for investing in the stock. Your task is to build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators. Leverage the provided research and data to address concerns and counter bearish arguments effectively.

Key points to focus on:
- Growth Potential: Highlight the company's market opportunities, revenue projections, and scalability.
- Competitive Advantages: Emphasize factors like unique products, strong branding, or dominant market positioning.
- Positive Indicators: Use financial health, industry trends, and recent positive news as evidence.
- Bear Counterpoints: Critically analyze the bear argument with specific data and sound reasoning, addressing concerns thoroughly and showing why the bull perspective holds stronger merit.
- Engagement: Present your argument in a conversational style, engaging directly with the bear analyst's points and debating effectively rather than just listing data.

You must also address reflections and learn from lessons and mistakes you made in the past."""

        # Create user message with context
        user_message = f"""Resources available:
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bear argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

Use this information to deliver a compelling bull argument, refute the bear's concerns, and engage in a dynamic debate that demonstrates the strengths of the bull position."""

        # Create agent and run
        agent = Agent(
            name="Bull Researcher",
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

            argument = f"Bull Analyst: {response_content}"

            new_investment_debate_state = {
                "history": history + "\n" + argument,
                "bull_history": bull_history + "\n" + argument,
                "bear_history": investment_debate_state.get("bear_history", ""),
                "current_response": argument,
                "count": investment_debate_state["count"] + 1,
            }

            return {
                "investment_debate_state": new_investment_debate_state,
                "sender": "Bull Researcher"
            }
        except Exception as e:
            error_msg = f"Error running bull researcher: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            argument = f"Bull Analyst: {error_msg}"
            new_investment_debate_state = {
                "history": history + "\n" + argument,
                "bull_history": bull_history + "\n" + argument,
                "bear_history": investment_debate_state.get("bear_history", ""),
                "current_response": argument,
                "count": investment_debate_state["count"] + 1,
            }
            return {
                "investment_debate_state": new_investment_debate_state,
                "sender": "Bull Researcher"
            }

    return bull_node
