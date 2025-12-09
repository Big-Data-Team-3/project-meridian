# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START

from agents_module import *
from agents_module.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        config: Dict[str, Any],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.config = config
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=["market", "information", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "information": Information analyst (combines news and social media analysis)
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes (using OpenAI Agents SDK - no ToolNodes needed)
        analyst_nodes = {}
        delete_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                model=self.config.get("quick_think_llm", "gpt-4o-mini")
            )
            delete_nodes["market"] = create_msg_delete()

        if "information" in selected_analysts:
            analyst_nodes["information"] = create_information_analyst(
                model=self.config.get("quick_think_llm", "gpt-4o-mini")
            )
            delete_nodes["information"] = create_msg_delete()

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                model=self.config.get("quick_think_llm", "gpt-4o-mini")
            )
            delete_nodes["fundamentals"] = create_msg_delete()

        # Create researcher and manager nodes (using OpenAI Agents SDK - model string instead of llm object)
        bull_researcher_node = create_bull_researcher(
            model=self.config.get("quick_think_llm", "gpt-4o-mini"),
            memory=self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            model=self.config.get("quick_think_llm", "gpt-4o-mini"),
            memory=self.bear_memory
        )
        research_manager_node = create_research_manager(
            model=self.config.get("deep_think_llm", "gpt-4o"),
            memory=self.invest_judge_memory
        )
        trader_node = create_trader(
            model=self.config.get("quick_think_llm", "gpt-4o-mini"),
            memory=self.trader_memory
        )

        # Create risk analysis nodes (using OpenAI Agents SDK)
        risky_analyst = create_risky_debator(
            model=self.config.get("quick_think_llm", "gpt-4o-mini")
        )
        neutral_analyst = create_neutral_debator(
            model=self.config.get("quick_think_llm", "gpt-4o-mini")
        )
        safe_analyst = create_safe_debator(
            model=self.config.get("quick_think_llm", "gpt-4o-mini")
        )
        risk_manager_node = create_risk_manager(
            model=self.config.get("deep_think_llm", "gpt-4o"),
            memory=self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        # Connect analysts in sequence
        # With OpenAI Agents SDK, tools are executed internally, so we go directly to message clear
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Analysts execute tools internally via OpenAI Agents SDK, so go directly to message clear
            workflow.add_edge(current_analyst, current_clear)

            # Connect to next analyst or to Bull Researcher if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, "Bull Researcher")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
