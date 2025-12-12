"""
LLM Planner Agent

The LLM Planner Agent analyzes user queries and generates structured execution plans
for dynamic graph construction. It acts as a supervisor above all specialized agents.
"""

import json
import time
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents_module.registry.registry import AgentRegistry
from agents_module.registry.initial_registry import get_default_registry
from .models import ExecutionPlan
from .config import PlannerConfig, DEFAULT_CONFIG
from .prompt_builder import PlannerPromptBuilder
from .validator import ExecutionPlanValidator


class PlannerAgent:
    """
    LLM Planner Agent that generates execution plans for dynamic graph construction.
    
    The planner analyzes queries, consults the agent capability registry, and
    generates structured plans specifying which agents to execute and in what order.
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        config: Optional[PlannerConfig] = None,
        llm: Optional[ChatOpenAI] = None
    ):
        """
        Initialize the Planner Agent.
        
        Args:
            registry: AgentRegistry instance (defaults to default registry)
            config: PlannerConfig instance (defaults to DEFAULT_CONFIG)
            llm: ChatOpenAI instance (created from config if not provided)
        """
        self.registry = registry or get_default_registry()
        self.config = config or DEFAULT_CONFIG
        self.prompt_builder = PlannerPromptBuilder(self.registry)
        self.validator = ExecutionPlanValidator(self.registry)
        
        # Initialize LLM
        if llm:
            self.llm = llm
        else:
            self.llm = ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
    
    def plan_workflow(
        self, 
        query: str, 
        context: Optional[List[Dict[str, Any]]] = None
    ) -> ExecutionPlan:
        """
        Generate an execution plan for a user query.
        
        Args:
            query: User's query string
            context: Optional conversation context (list of message dicts with 'role' and 'content')
            
        Returns:
            ExecutionPlan instance
            
        Raises:
            ValueError: If planning fails and no fallback is available
        """
        # Limit context to max_context_messages
        if context:
            context = context[-self.config.max_context_messages:]
        
        try:
            # Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(query, context)
            
            # Call LLM with structured output
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            start_time = time.time()
            response = self.llm.invoke(messages)
            elapsed = time.time() - start_time
            
            if elapsed > self.config.timeout_seconds:
                raise TimeoutError(f"Planner call exceeded timeout of {self.config.timeout_seconds}s")
            
            # Parse JSON response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json(content)
            
            # Parse and validate
            plan_dict = json.loads(json_str)
            plan = ExecutionPlan(**plan_dict)
            
            # Validate plan against registry
            is_valid, error = self.validator.validate(plan)
            if not is_valid:
                # Try to fix common issues
                fixed_plan, was_fixed, fix_error = self.validator.validate_and_fix(plan)
                if was_fixed:
                    plan = fixed_plan
                else:
                    raise ValueError(f"Invalid execution plan: {error}. Fix attempt failed: {fix_error}")
            
            return plan
            
        except Exception as e:
            # Fallback to simple plan if enabled
            if self.config.fallback_enabled:
                return self._create_fallback_plan(query)
            else:
                raise ValueError(f"Planning failed: {str(e)}")
    
    def _extract_json(self, content: str) -> str:
        """
        Extract JSON from LLM response (handles markdown code blocks).
        
        Args:
            content: LLM response content
            
        Returns:
            JSON string
        """
        # Try to find JSON in code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()
        
        # Try to find JSON object directly
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return content[start:end]
        
        # Return as-is and let JSON parser handle it
        return content.strip()
    
    def _create_fallback_plan(self, query: str) -> ExecutionPlan:
        """
        Create a simple fallback plan when planner fails.
        
        Args:
            query: User query
            
        Returns:
            Simple ExecutionPlan with just market_analyst
        """
        return ExecutionPlan(
            agents=["market_analyst"],
            execution_order=["market_analyst"],
            criticality_map={"market_analyst": "critical"},
            termination_conditions={},
            reasoning=f"Fallback plan for query: {query[:100]}",
            estimated_duration=45.0,
            estimated_cost=0.05
        )
    
    def get_registry_summary(self) -> str:
        """
        Get a summary of available agents for debugging.
        
        Returns:
            Human-readable summary string
        """
        return self.registry.get_capabilities_summary()

