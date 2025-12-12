# TradingAgents/graph/setup.py

import time
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START

from agents_module import *
from agents_module.utils.agent_states import AgentState
from .planner.models import ExecutionPlan
from .agent_factory_map import AgentFactoryMap

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
        
        # Create agent factory map
        memories = {
            "bull_memory": bull_memory,
            "bear_memory": bear_memory,
            "trader_memory": trader_memory,
            "invest_judge_memory": invest_judge_memory,
            "risk_manager_memory": risk_manager_memory,
        }
        self.factory_map = AgentFactoryMap(config, memories)

    def setup_graph(
        self, 
        execution_plan: ExecutionPlan,
        validate: bool = True
    ):
        """
        Set up and compile the agent workflow graph dynamically from ExecutionPlan.
        
        This method constructs the graph at runtime based on the planner's execution plan.
        The graph structure is determined by the plan, not pre-configured.

        Args:
            execution_plan: ExecutionPlan from LLM Planner specifying agents and order
            validate: Whether to validate the constructed graph matches the plan
            
        Returns:
            Compiled LangGraph workflow
        """
        start_time = time.time()

        if len(execution_plan.agents) == 0:
            raise ValueError("Execution plan must contain at least one agent!")
        
        # Validate plan structure
        is_valid, error = execution_plan.validate()
        if not is_valid:
            raise ValueError(f"Invalid execution plan: {error}")

        # Create workflow
        workflow = StateGraph(AgentState)

        # Create nodes dynamically based on execution plan
        nodes_created = {}
        for agent_id in execution_plan.agents:
            node_func = self.factory_map.create_agent_node(agent_id)
            node_name = self.factory_map.get_node_name(agent_id)
            workflow.add_node(node_name, node_func)
            nodes_created[agent_id] = node_name
            
            # Add message clear node for analysts
            if self.factory_map.is_analyst(agent_id):
                clear_node_name = f"Msg Clear {node_name}"
                clear_node_func = create_msg_delete()
                workflow.add_node(clear_node_name, clear_node_func)
                nodes_created[f"{agent_id}_clear"] = clear_node_name
        
        # Build edges dynamically based on execution_order
        if len(execution_plan.execution_order) == 0:
            raise ValueError("Execution plan execution_order cannot be empty")
        
        # Start with first agent
        first_agent_id = execution_plan.execution_order[0]
        first_node_name = nodes_created[first_agent_id]
        workflow.add_edge(START, first_node_name)

        # Connect agents in sequence according to execution_order
        for i, agent_id in enumerate(execution_plan.execution_order):
            node_name = nodes_created[agent_id]
            
            # For analysts, connect to message clear node
            if self.factory_map.is_analyst(agent_id):
                clear_node_name = nodes_created[f"{agent_id}_clear"]
                workflow.add_edge(node_name, clear_node_name)
                current_node = clear_node_name
            else:
                current_node = node_name
            
            # Connect to next agent or END
            if i < len(execution_plan.execution_order) - 1:
                next_agent_id = execution_plan.execution_order[i + 1]
                next_node_name = nodes_created[next_agent_id]
                workflow.add_edge(current_node, next_node_name)
            else:
                # Last agent - connect to END
                workflow.add_edge(current_node, END)
        
        # Add conditional edges for debate agents if present
        debate_agents = ["bull_researcher", "bear_researcher"]
        if any(agent_id in execution_plan.agents for agent_id in debate_agents):
            # Add debate conditional logic
            if "bull_researcher" in nodes_created and "bear_researcher" in nodes_created:
                bull_node = nodes_created["bull_researcher"]
                bear_node = nodes_created["bear_researcher"]
                
            workflow.add_conditional_edges(
                    bull_node,
                self.conditional_logic.should_continue_debate,
                {
                        "Bear Researcher": bear_node,
                        "Research Manager": nodes_created.get("research_manager", END),
                },
            )
            workflow.add_conditional_edges(
                    bear_node,
                self.conditional_logic.should_continue_debate,
                {
                        "Bull Researcher": bull_node,
                        "Research Manager": nodes_created.get("research_manager", END),
                },
            )
        
        # Add conditional edges for risk agents if present
        risk_agents = ["risky_debator", "safe_debator", "neutral_debator"]
        if any(agent_id in execution_plan.agents for agent_id in risk_agents):
            risky_node = nodes_created.get("risky_debator")
            safe_node = nodes_created.get("safe_debator")
            neutral_node = nodes_created.get("neutral_debator")
            risk_judge_node = nodes_created.get("risk_manager")
            
            if risky_node:
                workflow.add_conditional_edges(
                    risky_node,
                self.conditional_logic.should_continue_risk_analysis,
                {
                        "Safe Analyst": safe_node or END,
                        "Risk Judge": risk_judge_node or END,
                },
                )
            if safe_node:
                workflow.add_conditional_edges(
                    safe_node,
                self.conditional_logic.should_continue_risk_analysis,
                {
                        "Neutral Analyst": neutral_node or END,
                        "Risk Judge": risk_judge_node or END,
                },
                )
            if neutral_node:
                workflow.add_conditional_edges(
                    neutral_node,
                self.conditional_logic.should_continue_risk_analysis,
                {
                        "Risky Analyst": risky_node or END,
                        "Risk Judge": risk_judge_node or END,
                },
                )
        
        # Validate construction time
        construction_time = time.time() - start_time
        if construction_time > 0.1:  # 100ms threshold
            print(f"⚠️  Graph construction took {construction_time:.3f}s (target: <0.1s)")
        
        # Validate graph matches plan if requested
        if validate:
            self._validate_graph(workflow, execution_plan, nodes_created)

        # Compile and return
        return workflow.compile()
    
    def _validate_graph(
        self, 
        workflow: StateGraph, 
        execution_plan: ExecutionPlan,
        nodes_created: Dict[str, str]
    ) -> None:
        """
        Validate that constructed graph matches execution plan.
        
        Args:
            workflow: Constructed StateGraph
            execution_plan: Original execution plan
            nodes_created: Mapping of agent_id to node names
        """
        # Check that all agents from plan have nodes
        for agent_id in execution_plan.agents:
            if agent_id not in nodes_created:
                raise ValueError(f"Graph validation failed: agent '{agent_id}' not found in constructed graph")
        
        # Check execution order is respected (basic check)
        if len(execution_plan.execution_order) != len(set(execution_plan.execution_order)):
            raise ValueError("Graph validation failed: execution_order contains duplicates")
    
    # Legacy method for backward compatibility (deprecated)
    def setup_graph_legacy(
        self, 
        selected_analysts=["market", "information", "fundamentals"],
        include_debate: bool = True,
        include_risk: bool = True
    ):
        """
        Legacy method for backward compatibility.
        
        This method is deprecated. Use setup_graph() with ExecutionPlan instead.
        """
        # Convert legacy parameters to a simple execution plan
        agents = selected_analysts.copy()
        execution_order = selected_analysts.copy()
        criticality_map = {agent: "critical" for agent in selected_analysts}
        
        if include_debate:
            agents.extend(["bull_researcher", "bear_researcher", "research_manager", "trader"])
            execution_order.extend(["bull_researcher", "bear_researcher", "research_manager", "trader"])
            criticality_map.update({
                "bull_researcher": "non-critical",
                "bear_researcher": "non-critical",
                "research_manager": "critical",
                "trader": "critical"
            })
        
        if include_risk:
            agents.extend(["risky_debator", "safe_debator", "neutral_debator", "risk_manager"])
            execution_order.extend(["risky_debator", "safe_debator", "neutral_debator", "risk_manager"])
            criticality_map.update({
                "risky_debator": "non-critical",
                "safe_debator": "non-critical",
                "neutral_debator": "non-critical",
                "risk_manager": "critical"
            })
        
        from .planner.models import ExecutionPlan
        legacy_plan = ExecutionPlan(
            agents=agents,
            execution_order=execution_order,
            criticality_map=criticality_map
        )
        
        return self.setup_graph(legacy_plan, validate=False)
