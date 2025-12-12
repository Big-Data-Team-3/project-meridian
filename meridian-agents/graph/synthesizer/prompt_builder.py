"""
Synthesizer Prompt Builder

Constructs prompts for the Final Synthesizer that include all agent outputs.
"""

from typing import Dict, Any, Optional
from ..orchestrator.models import AggregatedContext


class SynthesizerPromptBuilder:
    """
    Builds prompts for the Final Synthesizer.
    
    The prompt includes:
    - All successful agent outputs
    - Information about failed agents (if any)
    - Instructions for synthesizing a coherent answer
    """
    
    def build_system_prompt(self) -> str:
        """
        Build the system prompt for the synthesizer.
        
        Returns:
            System prompt string
        """
        return """You are a Final Synthesizer Agent responsible for merging multiple agent analyses into a coherent, unified investment recommendation.

Your task is to:
1. Review all successful agent outputs
2. Identify key insights from each agent
3. Resolve any conflicts or contradictions between agents
4. Synthesize a clear, actionable recommendation (BUY, SELL, or HOLD)
5. Provide detailed reasoning that references specific agent contributions
6. Assign a confidence level (0.0 to 1.0) based on agreement between agents

If some agents failed (non-critical), you should still provide a recommendation based on available information, but note the limitations.

Your response MUST be valid JSON matching the SynthesizerOutput schema."""
    
    def build_user_prompt(
        self,
        aggregated_context: AggregatedContext,
        original_query: Optional[str] = None
    ) -> str:
        """
        Build user prompt for synthesizer.
        
        Detects query type (news-only vs trading) and adjusts prompt accordingly.
        """
        """
        Build the user prompt with aggregated context.
        
        Args:
            aggregated_context: AggregatedContext with all agent outputs
            original_query: Optional original user query
            
        Returns:
            User prompt string
        """
        # Build agent outputs section
        agent_outputs_section = "## Agent Outputs\n\n"
        
        for agent_id, agent_output in aggregated_context.agent_outputs.items():
            agent_outputs_section += f"### {agent_id}\n"
            agent_outputs_section += f"Status: {agent_output.status}\n"
            agent_outputs_section += f"Payload: {str(agent_output.payload)[:500]}...\n\n"
        
        # Build failed agents section if any
        failed_agents_section = ""
        if aggregated_context.get_failed_agents():
            failed_agents_section = "\n## Failed Agents\n\n"
            for agent_id in aggregated_context.get_failed_agents():
                error = aggregated_context.errors.get(agent_id, {})
                criticality = aggregated_context.criticality_info.get(agent_id, "unknown")
                failed_agents_section += f"- {agent_id} ({criticality}): {error.get('message', 'Unknown error')}\n"
        
        # Build metadata section
        metadata_section = f"""
## Execution Metadata
- Total agents planned: {aggregated_context.metadata.get('total_agents_planned', 0)}
- Agents succeeded: {aggregated_context.metadata.get('agents_succeeded', 0)}
- Agents failed: {aggregated_context.metadata.get('agents_failed', 0)}
- Workflow aborted: {aggregated_context.workflow_aborted}
"""
        
        query_section = ""
        if original_query:
            query_section = f"\n## Original Query\n{original_query}\n"
        
        # Detect query type: news-only vs trading decision
        is_news_only_query = False
        if original_query:
            query_lower = original_query.lower()
            news_keywords = ["news", "sentiment", "summarize", "what's the news", "latest news", "recent news"]
            trading_keywords = ["should i", "buy", "sell", "trade", "investment", "recommendation", "decision"]
            
            # Check if it's a news-only query (has news keywords but no trading keywords)
            has_news_keyword = any(kw in query_lower for kw in news_keywords)
            has_trading_keyword = any(kw in query_lower for kw in trading_keywords)
            
            # Also check execution plan - if only information_analyst ran, it's likely news-only
            execution_plan = aggregated_context.execution_plan
            if execution_plan and isinstance(execution_plan, dict):
                agents = execution_plan.get("agents", [])
                if len(agents) == 1 and "information_analyst" in agents:
                    is_news_only_query = True
            elif has_news_keyword and not has_trading_keyword:
                is_news_only_query = True
        
        if is_news_only_query:
            # News-only query: Just summarize the news, no trading recommendation needed
            prompt = f"""{query_section}
{agent_outputs_section}
{failed_agents_section}
{metadata_section}

## Task
The user asked for news/sentiment information, NOT a trading recommendation. Your task is to:
1. Summarize the news and sentiment information from the information_analyst
2. Present it in a clear, organized format
3. Do NOT provide a BUY/SELL/HOLD recommendation
4. Focus on delivering the news summary the user requested

Return a JSON object with this structure:
{{
  "summary": "Comprehensive summary of the news and sentiment information",
  "reasoning": "Detailed explanation of the news context and key points",
  "agent_references": [
    {{"agent_id": "information_analyst", "contribution": "What this agent contributed"}}
  ],
  "confidence": 1.0,
  "key_factors": ["key news item 1", "key news item 2", ...],
  "risks": []  // Not applicable for news-only queries
}}

Important:
- This is a NEWS SUMMARY query, not a trading decision query
- Do NOT include a "recommendation" field (BUY/SELL/HOLD)
- Focus on summarizing the news content clearly and comprehensively
- Organize the information in a way that's useful for the user"""
        else:
            # Trading decision query: Generate recommendation
            prompt = f"""{query_section}
{agent_outputs_section}
{failed_agents_section}
{metadata_section}

## Task
Synthesize all agent outputs into a coherent investment recommendation. Consider:
1. What do the technical indicators suggest? (from market_analyst)
2. What do the fundamentals indicate? (from fundamentals_analyst)
3. What is the sentiment and news context? (from information_analyst)
4. What are the bullish and bearish perspectives? (from researchers)
5. What is the risk assessment? (from risk agents)

Provide a clear BUY/SELL/HOLD recommendation with:
- Detailed reasoning that references specific agent contributions
- Confidence level based on agreement between agents
- Key factors that influenced your decision
- Any risks or concerns identified

Return a JSON object with this structure:
{{
  "recommendation": "BUY|SELL|HOLD",
  "reasoning": "Detailed explanation...",
  "agent_references": [
    {{"agent_id": "market_analyst", "contribution": "What this agent contributed"}},
    ...
  ],
  "confidence": 0.75,
  "summary": "Brief summary",
  "key_factors": ["factor1", "factor2", ...],
  "risks": ["risk1", "risk2", ...]
}}

Important:
- If agents disagree, explain the conflict and why you chose your recommendation
- If workflow was aborted due to critical failure, note this limitation
- Confidence should reflect agreement: high if agents agree, lower if they conflict
- Always provide actionable reasoning, not just a recommendation"""
        
        return prompt
    
    def build_fallback_prompt(self, aggregated_context: AggregatedContext) -> str:
        """
        Build a fallback prompt when most agents failed.
        
        Args:
            aggregated_context: AggregatedContext with limited outputs
            
        Returns:
            Fallback prompt string
        """
        return f"""Generate a recommendation based on limited information.

Available outputs: {len(aggregated_context.agent_outputs)} successful agents
Failed agents: {len(aggregated_context.get_failed_agents())}

Return JSON:
{{
  "recommendation": "HOLD",
  "reasoning": "Limited analysis available due to agent failures. Recommend HOLD until more information is available.",
  "agent_references": [],
  "confidence": 0.3,
  "summary": "Insufficient data for confident recommendation"
}}"""

