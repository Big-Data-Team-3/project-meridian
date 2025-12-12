"""
Agent Factory Map

Maps agent IDs to their factory functions for dynamic node creation.
"""

from typing import Dict, Callable, Any
from agents_module import (
    create_market_analyst,
    create_fundamentals_analyst,
    create_information_analyst,
    create_bull_researcher,
    create_bear_researcher,
    create_research_manager,
    create_trader,
    create_risky_debator,
    create_safe_debator,
    create_neutral_debator,
    create_risk_manager,
    create_msg_delete,
)


class AgentFactoryMap:
    """
    Maps agent IDs to their factory functions and configuration.
    """
    
    def __init__(self, config: Dict[str, Any], memories: Dict[str, Any]):
        """
        Initialize factory map.
        
        Args:
            config: Configuration dictionary
            memories: Dictionary of memory instances (bull_memory, bear_memory, etc.)
        """
        self.config = config
        self.memories = memories
        
        # Map agent_id to (factory_function, requires_memory, model_type)
        self._factory_map: Dict[str, tuple] = {
            "market_analyst": (create_market_analyst, False, "quick"),
            "fundamentals_analyst": (create_fundamentals_analyst, False, "quick"),
            "information_analyst": (create_information_analyst, False, "quick"),
            "bull_researcher": (create_bull_researcher, True, "quick"),
            "bear_researcher": (create_bear_researcher, True, "quick"),
            "research_manager": (create_research_manager, True, "deep"),
            "trader": (create_trader, True, "quick"),
            "risky_debator": (create_risky_debator, False, "quick"),
            "safe_debator": (create_safe_debator, False, "quick"),
            "neutral_debator": (create_neutral_debator, False, "quick"),
            "risk_manager": (create_risk_manager, True, "deep"),
        }
        
        # Map agent_id to memory key
        self._memory_map: Dict[str, str] = {
            "bull_researcher": "bull_memory",
            "bear_researcher": "bear_memory",
            "research_manager": "invest_judge_memory",
            "trader": "trader_memory",
            "risk_manager": "risk_manager_memory",
        }
    
    def create_agent_node(self, agent_id: str) -> Callable:
        """
        Create an agent node function for the given agent_id.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent node function
        """
        if agent_id not in self._factory_map:
            raise ValueError(f"Unknown agent_id: {agent_id}")
        
        factory_func, requires_memory, model_type = self._factory_map[agent_id]
        
        # Get model name
        if model_type == "quick":
            model = self.config.get("quick_think_llm", "gpt-4o-mini")
        else:
            model = self.config.get("deep_think_llm", "gpt-4o")
        
        # Create agent with appropriate parameters
        if requires_memory:
            memory_key = self._memory_map[agent_id]
            memory = self.memories.get(memory_key)
            if memory is None:
                raise ValueError(f"Memory '{memory_key}' not found for agent '{agent_id}'")
            return factory_func(model=model, memory=memory)
        else:
            return factory_func(model=model)
    
    def get_node_name(self, agent_id: str) -> str:
        """
        Get the display name for an agent node.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Human-readable node name
        """
        name_map = {
            "market_analyst": "Market Analyst",
            "fundamentals_analyst": "Fundamentals Analyst",
            "information_analyst": "Information Analyst",
            "bull_researcher": "Bull Researcher",
            "bear_researcher": "Bear Researcher",
            "research_manager": "Research Manager",
            "trader": "Trader",
            "risky_debator": "Risky Analyst",
            "safe_debator": "Safe Analyst",
            "neutral_debator": "Neutral Analyst",
            "risk_manager": "Risk Judge",
        }
        return name_map.get(agent_id, agent_id.replace("_", " ").title())
    
    def is_analyst(self, agent_id: str) -> bool:
        """
        Check if agent is an analyst (needs message clearing).
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent is an analyst
        """
        analyst_ids = ["market_analyst", "fundamentals_analyst", "information_analyst"]
        return agent_id in analyst_ids

