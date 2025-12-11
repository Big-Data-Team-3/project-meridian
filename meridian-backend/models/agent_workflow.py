"""
Agent workflow configuration models.
Defines workflow types and their configurations.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from models.query_intent import QueryIntent


class AgentWorkflowConfig(BaseModel):
    """Configuration for an agent workflow."""
    
    workflow_type: str = Field(..., description="Type of workflow: 'direct_response', 'single_agent', 'multi_agent', 'full_workflow', 'focused', 'selective', 'analysis_only', 'trading_only'")
    agents: List[str] = Field(default_factory=list, description="List of agent types to include")
    timeout_seconds: int = Field(..., description="Timeout in seconds for this workflow")
    include_debate: bool = Field(default=False, description="Whether to include debate phase")
    include_risk: bool = Field(default=False, description="Whether to include risk analysis")
    focus: Optional[str] = Field(None, description="Focus area for focused workflows (e.g., 'sentiment_only', 'technical_only')")
    selective_agents: Optional[List[str]] = Field(None, description="Specific agents to run for selective workflow (overrides default sequence)")
    skip_agents: Optional[List[str]] = Field(None, description="Agents to skip in the workflow")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional workflow metadata")


class AgentWorkflowMapper:
    """Maps query intents to agent workflow configurations."""
    
    @staticmethod
    def get_workflow_config(intent: QueryIntent) -> AgentWorkflowConfig:
        """
        Get workflow configuration for a given query intent.
        
        Args:
            intent: QueryIntent enum value
            
        Returns:
            AgentWorkflowConfig for the intent
        """
        workflows = {
            QueryIntent.SIMPLE_CHAT: AgentWorkflowConfig(
                workflow_type="direct_response",
                agents=[],
                timeout_seconds=30,
                include_debate=False,
                include_risk=False
            ),
            QueryIntent.BASIC_INFO: AgentWorkflowConfig(
                workflow_type="single_agent",
                agents=["information"],
                timeout_seconds=45,
                include_debate=False,
                include_risk=False
            ),
            QueryIntent.TECHNICAL_ANALYSIS: AgentWorkflowConfig(
                workflow_type="single_agent",
                agents=["market"],
                timeout_seconds=60,
                include_debate=False,
                include_risk=False
            ),
            QueryIntent.FUNDAMENTAL_ANALYSIS: AgentWorkflowConfig(
                workflow_type="single_agent",
                agents=["fundamentals"],
                timeout_seconds=60,
                include_debate=False,
                include_risk=False
            ),
            QueryIntent.NEWS_SENTIMENT: AgentWorkflowConfig(
                workflow_type="focused",
                agents=["information"],
                timeout_seconds=45,
                include_debate=False,
                include_risk=False,
                focus="sentiment_only"
            ),
            QueryIntent.COMPREHENSIVE_TRADE: AgentWorkflowConfig(
                workflow_type="full_workflow",
                agents=["market", "fundamentals", "information"],
                timeout_seconds=300,
                include_debate=True,
                include_risk=True
            ),
            QueryIntent.PORTFOLIO_REVIEW: AgentWorkflowConfig(
                workflow_type="multi_agent",
                agents=["market", "fundamentals"],
                timeout_seconds=120,
                include_debate=False,
                include_risk=False
            ),
            QueryIntent.MARKET_OVERVIEW: AgentWorkflowConfig(
                workflow_type="multi_agent",
                agents=["market", "information"],
                timeout_seconds=90,
                include_debate=False,
                include_risk=False
            ),
            # Additional selective workflows based on query content analysis
            # These will be dynamically assigned by the enhanced orchestrator
        }
        
        return workflows.get(intent, workflows[QueryIntent.SIMPLE_CHAT])

