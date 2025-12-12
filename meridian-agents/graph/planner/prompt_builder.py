"""
Planner Prompt Builder

Constructs prompts for the LLM Planner Agent that include agent capability
registry information and query context.
"""

from typing import Dict, List, Any, Optional
from agents_module.registry.registry import AgentRegistry


class PlannerPromptBuilder:
    """
    Builds prompts for the LLM Planner Agent.
    
    The prompt includes:
    - Agent capability registry (all available agents and their characteristics)
    - User query
    - Conversation context (if available)
    - Instructions for generating execution plans
    """
    
    def __init__(self, registry: AgentRegistry):
        """
        Initialize prompt builder.
        
        Args:
            registry: AgentRegistry instance to access agent capabilities
        """
        self.registry = registry
    
    def build_system_prompt(self) -> str:
        """
        Build the system prompt for the planner.
        
        Returns:
            System prompt string
        """
        return """You are an LLM Planner Agent responsible for analyzing user queries and generating execution plans for a multi-agent financial analysis system.

Your task is to:
1. Analyze the user query to understand what type of financial analysis is needed
2. Select appropriate agents from the available agent registry
3. Determine the execution order based on agent dependencies
4. Classify each agent as critical or non-critical
5. Generate a structured execution plan in JSON format

Available agents and their capabilities are provided in the agent registry below.

CRITICAL AGENTS are those whose failure would invalidate the entire workflow or produce unreliable results.
NON-CRITICAL AGENTS provide supplementary information but are not essential for a valid response.

## CRITICAL RULE: SINGLE-AGENT QUERIES
When a query asks for a SPECIFIC type of analysis (news, sentiment, technical, fundamental), you MUST use ONLY the relevant single agent. DO NOT include other agents.

Examples:
- "What's the news on Apple?" → ONLY information_analyst
- "Technical analysis of TSLA" → ONLY market_analyst  
- "Apple's financials" → ONLY fundamentals_analyst
- "Should I buy Apple?" → Multiple agents (comprehensive analysis)

Consider:
- Agent dependencies (some agents must run before others)
- Query complexity (simple queries may not need all agents)
- Cost and performance implications
- Whether partial or full analysis is needed
- Query keywords: "news", "sentiment", "technical", "fundamentals", "should I buy", "investment"

Your response MUST be valid JSON matching the ExecutionPlan schema."""
    
    def build_user_prompt(
        self, 
        query: str, 
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build the user prompt with query and context.
        
        Args:
            query: User's current query
            context: Optional conversation context (list of messages)
            
        Returns:
            User prompt string
        """
        # Get agent registry as JSON
        registry_json = self.registry.get_registry_json(include_metadata=True)
        
        # Build context section if available
        context_section = ""
        if context:
            context_section = "\n\n## Conversation Context\n"
            context_section += "Recent conversation history (for reference):\n"
            for msg in context:  # Context is already limited by caller
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                context_section += f"- {role}: {content[:200]}...\n"  # Truncate long messages
        
        prompt = f"""## User Query
{query}
{context_section}

## Agent Capability Registry
{registry_json}

## Task
Analyze the user query and generate an execution plan. Consider:
1. What type of analysis is needed? (technical, fundamental, sentiment, news, comprehensive)
2. Which agents are required?
3. What is the correct execution order (respecting dependencies)?
4. Which agents are critical vs non-critical?

## SINGLE-AGENT QUERY GUIDELINES (CRITICAL)
For queries asking about SPECIFIC topics, use ONLY the relevant single agent:

1. COMPANY INFORMATION / NEWS/SENTIMENT QUERIES → Use ONLY information_analyst
   - Examples: "What's the news on Apple?", "Tesla social media sentiment", "Latest news about Microsoft", "What's Microsoft's main products?", "What does Apple do?", "Tell me about Tesla", "What is NVIDIA's business?"
   - Keywords: "news", "sentiment", "social media", "announcements", "buzz", "trending", "products", "business", "what does", "tell me about", "what is", "company", "main products", "business model"
   - IMPORTANT: Any query asking about a company's business, products, or general information should use information_analyst
   - DO NOT include other agents for these queries

2. TECHNICAL ANALYSIS QUERIES → Use ONLY market_analyst
   - Examples: "Technical analysis of AAPL", "Show me charts for TSLA", "Moving averages for MSFT"
   - Keywords: "technical", "charts", "indicators", "RSI", "MACD", "trends"
   - DO NOT include other agents for these queries

3. FUNDAMENTAL ANALYSIS QUERIES → Use ONLY fundamentals_analyst
   - Examples: "Apple's financials", "Tesla earnings", "Microsoft balance sheet"
   - Keywords: "fundamentals", "financials", "earnings", "P/E ratio", "balance sheet"
   - DO NOT include other agents for these queries

4. COMPREHENSIVE/INVESTMENT QUERIES → Use multiple agents
   - Examples: "Should I buy Apple?", "Is Tesla a good investment?", "Analyze MSFT for trading"
   - Keywords: "should I buy", "investment", "trading decision", "comprehensive analysis"
   - Include: market_analyst, fundamentals_analyst, information_analyst, and debate/risk phases

## CRITICAL RULE: ALL COMPANY QUERIES REQUIRE AT LEAST ONE AGENT
- If a query mentions a company name or ticker symbol, you MUST include at least one agent
- For general company information queries (products, business, what does X do), use information_analyst
- NEVER return an empty agents list for queries about companies or stocks

Return a JSON object with this structure:
{{
  "agents": ["agent_id1", "agent_id2", ...],
  "execution_order": ["agent_id1", "agent_id2", ...],
  "criticality_map": {{
    "agent_id1": "critical",
    "agent_id2": "non-critical"
  }},
  "termination_conditions": {{}},
  "reasoning": "Brief explanation of your plan",
  "estimated_duration": 0.0,
  "estimated_cost": 0.0
}}

Important:
- execution_order must contain exactly the same agents as agents list
- All agents in agents list must have entries in criticality_map
- Criticality must be either "critical" or "non-critical"
- Respect agent dependencies from the registry
- FOR COMPANY INFORMATION/NEWS/SENTIMENT QUERIES: Use ONLY information_analyst (no other agents)
- FOR TECHNICAL QUERIES: Use ONLY market_analyst (no other agents)
- FOR FUNDAMENTAL QUERIES: Use ONLY fundamentals_analyst (no other agents)
- Only use multiple agents for comprehensive investment/trading decision queries
- CRITICAL: If a query mentions a company/ticker, you MUST include at least one agent (never return empty agents list)
- For general company info queries ("what does X do", "what are X's products"), use information_analyst"""
        
        return prompt
    
    def build_fallback_prompt(self, query: str) -> str:
        """
        Build a fallback prompt for simple queries when planner fails.
        
        Args:
            query: User's query
            
        Returns:
            Fallback prompt string
        """
        return f"""Generate a simple execution plan for: "{query}"

Use a minimal plan with just market_analyst as critical agent.

Return JSON:
{{
  "agents": ["market_analyst"],
  "execution_order": ["market_analyst"],
  "criticality_map": {{"market_analyst": "critical"}},
  "termination_conditions": {{}},
  "reasoning": "Fallback plan for simple query"
}}"""

