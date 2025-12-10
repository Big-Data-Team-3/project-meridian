"""
Agent orchestration service.
Routes queries to appropriate agent service endpoints based on intent.
"""
import os
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from models.query_intent import QueryIntent
from models.agent_workflow import AgentWorkflowMapper, AgentWorkflowConfig
from services.query_classifier import get_query_classifier

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Service for orchestrating agent workflows."""
    
    def __init__(self):
        """Initialize agent orchestrator."""
        self.classifier = get_query_classifier()
        self.workflow_mapper = AgentWorkflowMapper()
        # In Docker, prefer container name over host.docker.internal for reliability
        agents_base_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
        if "host.docker.internal" in agents_base_url:
            # Use container name instead - more reliable for Docker-to-Docker communication
            agents_base_url = "http://meridian-agents:8001"
            logger.info(f"Detected host.docker.internal, using container name instead: {agents_base_url}")
        self.agents_base_url = agents_base_url
    
    def classify_and_get_workflow(
        self,
        query: str,
        conversation_context: Optional[list] = None
    ) -> Tuple[QueryIntent, AgentWorkflowConfig]:
        """
        Classify query and get workflow configuration.
        
        Args:
            query: User query text
            conversation_context: Optional conversation history
            
        Returns:
            Tuple of (QueryIntent, AgentWorkflowConfig)
        """
        intent = self.classifier.classify(query, conversation_context)
        workflow = self.workflow_mapper.get_workflow_config(intent)
        
        logger.info(
            f"Query classified: intent={intent.value}, "
            f"workflow={workflow.workflow_type}, agents={workflow.agents}"
        )
        
        return intent, workflow
    
    def get_agent_endpoint(self, workflow: AgentWorkflowConfig) -> tuple[Optional[str], int]:
        """
        Get the appropriate agent service endpoint and timeout for a workflow.
        
        Args:
            workflow: AgentWorkflowConfig
            
        Returns:
            Tuple of (endpoint URL, timeout_seconds). Returns (None, timeout) for direct_response.
        """
        base_url = self.agents_base_url.rstrip('/')
        
        if workflow.workflow_type == "direct_response":
            # No agent endpoint needed - handled directly
            return None, workflow.timeout_seconds
        
        elif workflow.workflow_type == "single_agent":
            agent_type = workflow.agents[0] if workflow.agents else "market"
            return f"{base_url}/analyze/single/{agent_type}", workflow.timeout_seconds
        
        elif workflow.workflow_type == "multi_agent":
            return f"{base_url}/analyze/multi", workflow.timeout_seconds
        
        elif workflow.workflow_type == "focused":
            return f"{base_url}/analyze/focused", workflow.timeout_seconds
        
        elif workflow.workflow_type == "full_workflow":
            return f"{base_url}/analyze", workflow.timeout_seconds
        
        else:
            # Fallback to full workflow
            logger.warning(f"Unknown workflow type: {workflow.workflow_type}, using full workflow")
            return f"{base_url}/analyze", workflow.timeout_seconds
    
    def prepare_agent_request(
        self,
        company_name: str,
        trade_date: str,
        workflow: AgentWorkflowConfig,
        conversation_context: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Prepare request payload for agent service.
        
        Args:
            company_name: Company name or ticker
            trade_date: Trade date in YYYY-MM-DD format
            workflow: AgentWorkflowConfig
            conversation_context: Optional conversation history
            
        Returns:
            Request payload dictionary
        """
        payload = {
            "company_name": company_name,
            "trade_date": trade_date
        }
        
        if conversation_context:
            # Convert to format expected by agent service
            payload["conversation_context"] = [
                {
                    "id": msg.get("id", f"msg-{i}"),
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "metadata": msg.get("metadata")
                }
                for i, msg in enumerate(conversation_context)
            ]
        
        # Add workflow-specific parameters
        if workflow.workflow_type == "multi_agent":
            payload["agents"] = workflow.agents
            payload["include_debate"] = workflow.include_debate
            payload["include_risk"] = workflow.include_risk
        
        if workflow.workflow_type == "focused":
            payload["focus"] = workflow.focus
        
        if workflow.workflow_type == "full_workflow":
            # Full workflow uses default agents, but we can pass debate/risk flags if needed
            # Note: The existing /analyze endpoint doesn't support these flags yet
            # This is for future enhancement
            pass
        
        return payload


# Singleton instance
_agent_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Get or create agent orchestrator singleton."""
    global _agent_orchestrator
    if _agent_orchestrator is None:
        _agent_orchestrator = AgentOrchestrator()
    return _agent_orchestrator

