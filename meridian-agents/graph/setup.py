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
        self, 
        selected_analysts=["market", "information", "fundamentals"],
        include_debate: bool = True,
        include_risk: bool = True
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "information": Information analyst (combines news and social media analysis)
                - "fundamentals": Fundamentals analyst
            include_debate (bool): Whether to include research debate phase (Bull/Bear/Research Manager)
            include_risk (bool): Whether to include risk analysis phase (Risky/Safe/Neutral/Risk Judge)
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

        # Conditionally create researcher and manager nodes only if debate is needed
        bull_researcher_node = None
        bear_researcher_node = None
        research_manager_node = None
        trader_node = None
        
        if include_debate:
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

        # Conditionally create risk analysis nodes only if risk analysis is needed
        risky_analyst = None
        neutral_analyst = None
        safe_analyst = None
        risk_manager_node = None
        
        if include_risk:
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

        # Conditionally add debate/research nodes only if debate is needed
        if include_debate:
            workflow.add_node("Bull Researcher", bull_researcher_node)
            workflow.add_node("Bear Researcher", bear_researcher_node)
            workflow.add_node("Research Manager", research_manager_node)
            workflow.add_node("Trader", trader_node)

        # Conditionally add risk analysis nodes only if risk analysis is needed
        if include_risk:
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

            # Connect to next analyst or determine next phase based on workflow configuration
            if i < len(selected_analysts) - 1:
                # More analysts to process
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                # Last analyst - determine next phase based on workflow flags
                if include_debate:
                    # Connect to debate phase
                    workflow.add_edge(current_clear, "Bull Researcher")
                elif include_risk:
                    # Skip debate, go directly to risk analysis
                    workflow.add_edge(current_clear, "Risky Analyst")
                else:
                    # No debate or risk - end after analysts
                    workflow.add_edge(current_clear, END)

        # Conditionally add debate phase edges only if debate is enabled
        if include_debate:
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
            
            # After trader, determine next phase
            if include_risk:
                # Connect trader to risk analysis
                workflow.add_edge("Trader", "Risky Analyst")
            else:
                # No risk analysis - end after trader
                workflow.add_edge("Trader", END)

        # Conditionally add risk analysis phase edges only if risk analysis is enabled
        if include_risk:
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
            # Risk Judge is always the final node in risk analysis phase
            workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
