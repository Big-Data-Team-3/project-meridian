"""
Final Synthesizer

The Final Synthesizer LLM merges all agent signals into a coherent final answer.
"""

import json
import time
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..orchestrator.models import AggregatedContext
from .models import SynthesizerOutput
from .config import SynthesizerConfig, DEFAULT_CONFIG
from .prompt_builder import SynthesizerPromptBuilder


class FinalSynthesizer:
    """
    Final Synthesizer that merges agent outputs into coherent answers.
    
    The synthesizer takes aggregated context from all agents and produces
    a unified recommendation with reasoning that references agent contributions.
    """
    
    def __init__(
        self,
        config: Optional[SynthesizerConfig] = None,
        llm: Optional[ChatOpenAI] = None
    ):
        """
        Initialize the Final Synthesizer.
        
        Args:
            config: SynthesizerConfig instance (defaults to DEFAULT_CONFIG)
            llm: ChatOpenAI instance (created from config if not provided)
        """
        self.config = config or DEFAULT_CONFIG
        self.prompt_builder = SynthesizerPromptBuilder()
        
        # Initialize LLM
        if llm:
            self.llm = llm
        else:
            self.llm = ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
    
    def synthesize(
        self,
        aggregated_context: AggregatedContext,
        original_query: Optional[str] = None
    ) -> SynthesizerOutput:
        """
        Synthesize agent outputs into a coherent final answer.
        
        Args:
            aggregated_context: AggregatedContext with all agent outputs
            original_query: Optional original user query for context
            
        Returns:
            SynthesizerOutput with recommendation and reasoning
            
        Raises:
            ValueError: If synthesis fails and no fallback is available
        """
        # Check if we have enough successful outputs
        if len(aggregated_context.agent_outputs) == 0:
            # No successful outputs - use fallback
            return self._create_fallback_output(aggregated_context)
        
        try:
            # Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(aggregated_context, original_query)
            
            # Call LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            start_time = time.time()
            response = self.llm.invoke(messages)
            elapsed = time.time() - start_time
            
            if elapsed > self.config.timeout_seconds:
                raise TimeoutError(f"Synthesizer call exceeded timeout of {self.config.timeout_seconds}s")
            
            # Parse JSON response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json(content)
            
            # Parse and validate
            output_dict = json.loads(json_str)
            synthesizer_output = SynthesizerOutput(**output_dict)
            
            return synthesizer_output
            
        except Exception as e:
            # Fallback to simple synthesis
            print(f"⚠️  Synthesizer failed: {str(e)}. Using fallback.")
            return self._create_fallback_output(aggregated_context)
    
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
    
    def _create_fallback_output(self, aggregated_context: AggregatedContext) -> SynthesizerOutput:
        """
        Create a fallback output when synthesis fails.
        
        Args:
            aggregated_context: Aggregated context
            
        Returns:
            Basic SynthesizerOutput with HOLD recommendation
        """
        # Try to extract any available information
        reasoning_parts = []
        
        if aggregated_context.workflow_aborted:
            reasoning_parts.append("Workflow was aborted due to critical agent failure.")
        
        if aggregated_context.get_failed_agents():
            reasoning_parts.append(f"{len(aggregated_context.get_failed_agents())} agents failed during execution.")
        
        if len(aggregated_context.agent_outputs) > 0:
            reasoning_parts.append(f"Analysis based on {len(aggregated_context.agent_outputs)} successful agent(s).")
        else:
            reasoning_parts.append("No agent outputs available.")
        
        reasoning = " ".join(reasoning_parts) + " Recommend HOLD until more information is available."
        
        return SynthesizerOutput(
            recommendation="HOLD",
            reasoning=reasoning,
            agent_references=[],
            confidence=0.2,
            summary="Limited analysis available. Recommend HOLD."
        )

