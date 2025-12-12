"""
Agent Capability Registry

Centralized registry for all agent capabilities. Used by the LLM Planner
to make informed decisions about agent selection and sequencing.
"""

from typing import Dict, List, Optional
import json
from .models import AgentCapability
from .versioning import RegistryVersion


class AgentRegistry:
    """
    Centralized registry for agent capabilities.
    
    The registry stores structured descriptions of all agents and provides
    methods for querying and accessing agent information. The LLM Planner
    uses this registry to understand available agents and their characteristics.
    """
    
    def __init__(self, version: Optional[RegistryVersion] = None):
        """
        Initialize the agent registry.
        
        Args:
            version: Optional registry version for tracking changes
        """
        self._agents: Dict[str, AgentCapability] = {}
        self._version = version or RegistryVersion()
    
    def register_agent(self, capability: AgentCapability) -> None:
        """
        Register an agent capability in the registry.
        
        Args:
            capability: AgentCapability instance to register
            
        Raises:
            ValueError: If agent_id already exists
        """
        if capability.agent_id in self._agents:
            raise ValueError(f"Agent with id '{capability.agent_id}' is already registered")
        
        self._agents[capability.agent_id] = capability
        self._version.increment_minor()  # New agent addition is a minor version change
    
    def get_agent(self, agent_id: str) -> Optional[AgentCapability]:
        """
        Get an agent capability by ID.
        
        Args:
            agent_id: Unique identifier of the agent
            
        Returns:
            AgentCapability if found, None otherwise
        """
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[AgentCapability]:
        """
        List all registered agents.
        
        Returns:
            List of all AgentCapability instances
        """
        return list(self._agents.values())
    
    def list_agent_ids(self) -> List[str]:
        """
        List all registered agent IDs.
        
        Returns:
            List of agent IDs
        """
        return list(self._agents.keys())
    
    def get_registry_json(self, include_metadata: bool = True) -> str:
        """
        Get the complete registry as JSON string.
        
        This is used by the LLM Planner to understand available agents
        and their capabilities.
        
        Args:
            include_metadata: Whether to include version and metadata
            
        Returns:
            JSON string representation of the registry
        """
        registry_data = {
            "agents": [agent.model_dump() for agent in self._agents.values()]
        }
        
        if include_metadata:
            registry_data["version"] = self._version.to_dict()
            registry_data["total_agents"] = len(self._agents)
        
        return json.dumps(registry_data, indent=2)
    
    def get_registry_dict(self) -> Dict:
        """
        Get the complete registry as dictionary.
        
        Returns:
            Dictionary representation of the registry
        """
        return {
            "agents": [agent.model_dump() for agent in self._agents.values()],
            "version": self._version.to_dict(),
            "total_agents": len(self._agents)
        }
    
    def get_capabilities_summary(self) -> str:
        """
        Get a human-readable summary of all agent capabilities.
        
        Returns:
            Formatted string summary
        """
        lines = [f"Agent Capability Registry (v{self._version})", "=" * 50, ""]
        
        for agent in self._agents.values():
            lines.append(f"Agent: {agent.agent_name} ({agent.agent_id})")
            lines.append(f"  Capabilities: {', '.join(agent.capabilities)}")
            lines.append(f"  Execution Time: ~{agent.execution_time_estimate}s")
            lines.append(f"  Criticality: {agent.criticality_default}")
            if agent.dependencies:
                lines.append(f"  Dependencies: {', '.join(agent.dependencies)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_agent_exists(self, agent_id: str) -> bool:
        """
        Check if an agent exists in the registry.
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            True if agent exists, False otherwise
        """
        return agent_id in self._agents
    
    def get_version(self) -> RegistryVersion:
        """
        Get the current registry version.
        
        Returns:
            RegistryVersion instance
        """
        return self._version
    
    def update_agent(self, agent_id: str, **updates) -> None:
        """
        Update an existing agent's capability description.
        
        Args:
            agent_id: ID of agent to update
            **updates: Fields to update (must match AgentCapability fields)
            
        Raises:
            ValueError: If agent_id doesn't exist
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent with id '{agent_id}' not found")
        
        current = self._agents[agent_id]
        updated_data = current.model_dump()
        updated_data.update(updates)
        
        self._agents[agent_id] = AgentCapability(**updated_data)
        self._version.increment_patch()  # Update is a patch version change

