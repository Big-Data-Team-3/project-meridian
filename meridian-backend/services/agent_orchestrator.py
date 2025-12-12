"""
Agent orchestration service.
Routes queries to appropriate agent service endpoints based on intent.
"""
import os
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from models.query_intent import QueryIntent

try:
    from pydantic import BaseModel, Field
    from typing import List

    class AgentSelectionResponse(BaseModel):
        """LLM response for agent selection."""
        selected_agents: List[str] = Field(description="List of selected agent names")
        reasoning: str = Field(description="Brief explanation of agent selection")

except ImportError:
    AgentSelectionResponse = None
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
        base_workflow = self.workflow_mapper.get_workflow_config(intent)

        # Optimize workflow based on query content analysis
        optimized_workflow = self.optimize_workflow_for_query(query, base_workflow, intent)

        logger.info(
            f"Query classified: intent={intent.value}, "
            f"base_workflow={base_workflow.workflow_type}, "
            f"optimized_workflow={optimized_workflow.workflow_type}, "
            f"agents={optimized_workflow.agents}"
        )

        return intent, optimized_workflow

    def analyze_query_for_agents(self, query: str, intent: QueryIntent) -> List[str]:
        """
        Use LLM to intelligently analyze query content and determine which specific agents are needed.

        Args:
            query: User query text
            intent: Classified intent

        Returns:
            List of agent names needed for this query
        """
        # For simple intents that don't need complex orchestration, return minimal agents
        # These are single-agent queries that should never use LLM selection
        simple_single_agent_intents = [
            QueryIntent.SIMPLE_CHAT,
            QueryIntent.BASIC_INFO,
            QueryIntent.TECHNICAL_ANALYSIS,  # Always market agent only
            QueryIntent.FUNDAMENTAL_ANALYSIS,  # Always fundamentals agent only
            QueryIntent.NEWS_SENTIMENT  # Always information agent only
        ]
        if intent in simple_single_agent_intents:
            return self._get_agents_for_simple_intent(intent)

        # For complex intents that may need multiple agents, use LLM to determine optimal combination
        # Only use LLM for queries that might legitimately need multiple agents
        if intent in [QueryIntent.COMPREHENSIVE_TRADE, QueryIntent.PORTFOLIO_REVIEW, QueryIntent.MARKET_OVERVIEW]:
            return self._llm_agent_selection(query, intent)

        # Fallback to basic agent selection
        return self._get_agents_for_simple_intent(intent)

    def _llm_agent_selection(self, query: str, intent: QueryIntent) -> List[str]:
        """
        Use LLM to intelligently select the optimal combination of agents for a query.

        Args:
            query: User query text
            intent: Classified intent

        Returns:
            List of agent names optimized for this query
        """
        if not self.classifier:
            # Fallback if classifier not available
            return self._get_agents_for_simple_intent(intent)

        # Short-circuit for obvious single-agent technical queries
        query_lower = query.lower()
        if intent == QueryIntent.TECHNICAL_ANALYSIS:
            technical_keywords = [
                'technical indicator', 'rsi', 'macd', 'moving average', 'bollinger',
                'stochastic', 'momentum', 'volume', 'price action', 'chart pattern',
                'support', 'resistance', 'trend', 'fibonacci', 'candlestick'
            ]
            if any(keyword in query_lower for keyword in technical_keywords):
                logger.info(f"Detected clear technical analysis query, using market agent only: {query}")
                return ["market"]

        # Build agent selection prompt
        agent_selection_prompt = self._build_agent_selection_prompt(query, intent)

        try:
            # Use the same LLM as the classifier for consistency
            response = self.classifier.client.chat.completions.create(
                model=self.classifier.model,
                messages=[
                    {"role": "system", "content": agent_selection_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                response_model=AgentSelectionResponse,
                max_retries=2,
                temperature=0.2  # Low temperature for consistent agent selection
            )

            if response and response.selected_agents:
                return response.selected_agents

        except Exception as e:
            logger.warning(f"LLM agent selection failed: {e}, using fallback")
            return self._get_agents_for_simple_intent(intent)

        # Final fallback
        return self._get_agents_for_simple_intent(intent)

    def _build_agent_selection_prompt(self, query: str, intent: QueryIntent) -> str:
        """Build the system prompt for LLM-based agent selection."""
        return f"""
        You are an expert AI orchestrator for a financial analysis system. Your task is to intelligently select the optimal combination of specialized agents to answer this query efficiently and effectively.

        AVAILABLE AGENTS:
        - market: Technical analysis, charts, indicators, price patterns
        - information: News analysis, sentiment, social media, current events
        - fundamentals: Financial statements, valuation, earnings, ratios
        - bull_researcher: Optimistic investment thesis and arguments
        - bear_researcher: Pessimistic investment thesis and counter-arguments
        - research_manager: Synthesizes research debate into balanced analysis
        - trader: Trading strategy, position sizing, entry/exit recommendations
        - risky_analyst: Aggressive growth opportunities, high-risk perspectives
        - neutral_analyst: Balanced risk assessment, moderate approaches
        - safe_analyst: Conservative capital preservation, risk mitigation
        - risk_judge: Final risk score and comprehensive risk analysis

        QUERY INTENT: {intent.value}

        SELECTION GUIDELINES:
        1. Select ONLY the agents that are truly necessary to answer the query
        2. Consider the cognitive load - fewer agents = faster, more focused response
        3. For simple factual queries, use minimal agents (1-2)
        4. For investment decisions, include research debate (bull/bear/researcher)
        5. For trading recommendations, include trader agent
        6. For risk assessments, include risk analysis agents
        7. Avoid redundant agents that would provide overlapping information
        8. Prioritize relevance over comprehensiveness

        EFFICIENCY PRINCIPLES:
        - "What is Apple's P/E ratio?" → fundamentals agent only
        - "Is Tesla overvalued?" → fundamentals + research debate
        - "Should I buy NVIDIA?" → fundamentals + research + trader + risk analysis
        - "Show me AAPL charts" → market agent only
        - "What are Apple's technical indicators?" → market agent only
        - "Apple's RSI and MACD values" → market agent only
        - "Technical analysis of TSLA" → market agent only
        - "What's the news on TSLA?" → information agent only

        Return a JSON object with the selected_agents list containing only the agent names needed.
        """

    def _get_agents_for_simple_intent(self, intent: QueryIntent) -> List[str]:
        """Fallback agent selection for simple intents."""
        agent_mapping = {
            QueryIntent.BASIC_INFO: ["information"],
            QueryIntent.TECHNICAL_ANALYSIS: ["market"],
            QueryIntent.FUNDAMENTAL_ANALYSIS: ["fundamentals"],
            QueryIntent.NEWS_SENTIMENT: ["information"],
            QueryIntent.MARKET_OVERVIEW: ["market", "information"],
            QueryIntent.PORTFOLIO_REVIEW: ["market", "fundamentals"],
            QueryIntent.COMPREHENSIVE_TRADE: ["market", "fundamentals", "information"],  # Minimal comprehensive
        }
        return agent_mapping.get(intent, ["information"])

    def optimize_workflow_for_query(self, query: str, base_workflow: AgentWorkflowConfig, intent: QueryIntent) -> AgentWorkflowConfig:
        """
        Optimize the workflow configuration based on intelligent LLM analysis to select the right agents.

        Args:
            query: User query text
            base_workflow: Original workflow configuration
            intent: Classified intent

        Returns:
            Optimized workflow configuration with intelligently selected agents
        """
        # For simple intents that are already well-optimized, keep as-is
        # These intents have single-agent workflows that should NOT be overridden
        simple_single_agent_intents = [
            QueryIntent.SIMPLE_CHAT,
            QueryIntent.TECHNICAL_ANALYSIS,  # Should stay single_agent
            QueryIntent.FUNDAMENTAL_ANALYSIS,  # Should stay single_agent
            QueryIntent.NEWS_SENTIMENT  # Should stay single_agent
        ]
        if intent in simple_single_agent_intents:
            return base_workflow

        # For all other intents, use LLM to determine optimal agent combination
        optimal_agents = self.analyze_query_for_agents(query, intent)

        # Reorder conditions to check simpler workflows FIRST (before selective)
        # This ensures single_agent and multi_agent are properly returned
        
        # Single agent workflow (1 agent)
        if len(optimal_agents) == 1:
            return AgentWorkflowConfig(
                workflow_type="single_agent",
                agents=optimal_agents,
                timeout_seconds=45,
                include_debate=False,
                include_risk=False
            )
        
        # Multi-agent workflow (2-3 agents)
        elif len(optimal_agents) <= 3:
            return AgentWorkflowConfig(
                workflow_type="multi_agent",
                agents=optimal_agents,
                timeout_seconds=60,
                include_debate=False,
                include_risk=False
            )
        
        # Selective workflow (4-5 agents - less than 60% of full workflow)
        elif len(optimal_agents) < 6:  # Less than 60% of full workflow (10 agents)
            return AgentWorkflowConfig(
                workflow_type="selective",
                agents=optimal_agents,
                timeout_seconds=max(45, len(optimal_agents) * 12),  # Dynamic timeout: 12s per agent, min 45s
                include_debate=any(agent in optimal_agents for agent in ["bull_researcher", "bear_researcher", "research_manager"]),
                include_risk=any(agent in optimal_agents for agent in ["risky_analyst", "neutral_analyst", "safe_analyst", "risk_judge"]),
                selective_agents=optimal_agents
            )
        
        # Full workflow (6+ agents - most of the workflow needed)
        else:
            return AgentWorkflowConfig(
                workflow_type="full_workflow",
                agents=["market", "fundamentals", "information"],  # Core data gathering agents
                timeout_seconds=300,
                include_debate=True,
                include_risk=True
            )

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

        elif workflow.workflow_type == "selective":
            return f"{base_url}/analyze/selective", workflow.timeout_seconds

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
        conversation_context: Optional[list] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare request payload for agent service.
        
        Args:
            company_name: Company name or ticker
            trade_date: Trade date in YYYY-MM-DD format
            workflow: AgentWorkflowConfig
            conversation_context: Optional conversation history
            query: Optional user query for dynamic agent selection
            
        Returns:
            Request payload dictionary
        """
        payload = {
            "company_name": company_name,
            "trade_date": trade_date
        }
        
        # Add query if provided (for dynamic agent selection)
        if query:
            payload["query"] = query
        
        if conversation_context:
            # Convert to format expected by agent service
            # ConversationMessage requires: id, role, content, timestamp (all required)
            import uuid
            from datetime import datetime
            
            formatted_context = []
            for i, msg in enumerate(conversation_context):
                # Ensure all required fields are present
                msg_id = msg.get("id")
                if not msg_id or not isinstance(msg_id, str) or not msg_id.strip():
                    msg_id = f"msg-{uuid.uuid4()}"
                
                role = msg.get("role", "user")
                if role not in ["user", "assistant", "system"]:
                    role = "user"  # Default to user if invalid
                
                content = msg.get("content", "")
                if not content or not isinstance(content, str):
                    content = str(content) if content else ""
                
                timestamp = msg.get("timestamp", "")
                if not timestamp or not isinstance(timestamp, str):
                    # Generate ISO timestamp if missing
                    timestamp = datetime.utcnow().isoformat() + "Z"
                
                formatted_context.append({
                    "id": msg_id,
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                    "metadata": msg.get("metadata") if msg.get("metadata") else None
                })
            
            payload["conversation_context"] = formatted_context
        
        # Add workflow-specific parameters
        if workflow.workflow_type == "multi_agent":
            payload["agents"] = workflow.agents
            payload["include_debate"] = workflow.include_debate
            payload["include_risk"] = workflow.include_risk
        
        if workflow.workflow_type == "focused":
            payload["focus"] = workflow.focus
        
        if workflow.workflow_type == "selective":
            # Selective workflow specifies exact agents to run
            payload["selective_agents"] = workflow.selective_agents or workflow.agents
            payload["include_debate"] = workflow.include_debate
            payload["include_risk"] = workflow.include_risk

        if workflow.workflow_type == "full_workflow":
            # Full workflow uses default agents, but we can pass debate/risk flags if needed
            # Note: The existing /analyze endpoint doesn't support these flags yet
            # This is for future enhancement
            pass
        
        # For single_agent workflows, pass selective_agents so streaming endpoint can use it
        if workflow.workflow_type == "single_agent" and workflow.agents:
            payload["selective_agents"] = workflow.agents
        
        return payload


# Singleton instance
_agent_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Get or create agent orchestrator singleton."""
    global _agent_orchestrator
    if _agent_orchestrator is None:
        _agent_orchestrator = AgentOrchestrator()
    return _agent_orchestrator

