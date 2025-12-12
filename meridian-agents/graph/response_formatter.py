"""
Response Formatter

Formats agent outputs to directly answer the user's original query.
Works for both single-agent and multi-agent scenarios (excluding workflow cases).
"""
from typing import Optional, Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from .orchestrator.models import AggregatedContext


class ResponseFormatter:
    """
    Formats agent outputs to directly answer the user's original query.
    Handles both single-agent and multi-agent scenarios.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model, temperature=0)
    
    def format_single_agent_response(
        self,
        original_query: str,
        agent_output: str,
        agent_type: Optional[str] = None
    ) -> str:
        """
        Format single agent output to directly answer the original query.
        
        Args:
            original_query: The user's original question
            agent_output: The raw output from the agent
            agent_type: Optional agent type for context
            
        Returns:
            Formatted response that directly answers the query
        """
        system_prompt = """You are a response formatter. Your job is to take an agent's analysis output and format it to directly answer the user's original question.

Guidelines:
1. Read the user's original query carefully
2. Extract the specific information requested from the agent output
3. Provide a concise, direct answer to the query
4. Include relevant context only if necessary
5. If the query asks for a specific metric/value (e.g., "What is the RSI?"), extract and present that value prominently
6. If the query asks for analysis, provide the relevant analysis sections
7. Do not include unnecessary information that doesn't relate to the query
8. Maintain accuracy - only use information present in the agent output
9. Format the response in a clear, readable way (use markdown if helpful)

If the agent output doesn't contain the requested information, say so clearly."""

        user_prompt = f"""Original User Query:
{original_query}

Agent Output ({agent_type or 'unknown'}):
{agent_output}

Please format the agent output to directly answer the user's query. Be concise and focused on what was asked."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            # Fallback: return agent output with a note
            return f"**Answer to: {original_query}**\n\n{agent_output}\n\n*Note: Response formatting failed, showing full agent output.*"
    
    def format_multi_agent_response(
        self,
        original_query: str,
        aggregated_context: AggregatedContext,
        agent_outputs_map: Dict[str, str]
    ) -> str:
        """
        Format multiple agent outputs to directly answer the original query.
        
        Args:
            original_query: The user's original question
            aggregated_context: Aggregated context from orchestrator
            agent_outputs_map: Map of agent_id -> report text from final_state
            
        Returns:
            Formatted response that directly answers the query using all agent outputs
        """
        system_prompt = """You are a response formatter. Your job is to take outputs from multiple agents and format them to directly answer the user's original question.

Guidelines:
1. Read the user's original query carefully
2. Extract the specific information requested from the relevant agent outputs
3. Combine information from multiple agents only if necessary to answer the query
4. Provide a concise, direct answer to the query
5. If the query asks for a specific metric/value, extract and present that value prominently
6. If the query asks for comprehensive analysis, synthesize information from relevant agents
7. Do not include unnecessary information that doesn't relate to the query
8. Maintain accuracy - only use information present in the agent outputs
9. Format the response in a clear, readable way (use markdown if helpful)
10. If multiple agents have relevant information, organize it logically

If the agent outputs don't contain the requested information, say so clearly."""

        # Build agent outputs section
        agent_outputs_section = "## Agent Outputs\n\n"
        for agent_id, output_text in agent_outputs_map.items():
            agent_status = aggregated_context.agent_statuses.get(agent_id, "unknown")
            agent_outputs_section += f"### {agent_id} (Status: {agent_status})\n"
            agent_outputs_section += f"{output_text}\n\n"
        
        # Add metadata about successful agents
        successful_agents = aggregated_context.get_successful_agents()
        metadata_section = f"## Execution Summary\n"
        metadata_section += f"- Successful agents: {', '.join(successful_agents)}\n"
        if aggregated_context.get_failed_agents():
            metadata_section += f"- Failed agents: {', '.join(aggregated_context.get_failed_agents())}\n"

        user_prompt = f"""Original User Query:
{original_query}

{agent_outputs_section}

{metadata_section}

Please format the agent outputs to directly answer the user's query. Be concise and focused on what was asked. Only use information from successful agents."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            # Fallback: combine outputs with a note
            combined_output = "\n\n---\n\n".join([
                f"**{agent_id}:**\n{output_text}"
                for agent_id, output_text in agent_outputs_map.items()
            ])
            return f"**Answer to: {original_query}**\n\n{combined_output}\n\n*Note: Response formatting failed, showing combined agent outputs.*"
    
    def generate_fallback_response(
        self,
        original_query: str,
        company_name: str,
        trade_date: str,
        context_messages: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate a direct LLM response when agent output is not available.
        
        Args:
            original_query: The user's original question
            company_name: Company name or ticker
            trade_date: Trade date
            context_messages: Optional conversation context
            
        Returns:
            LLM-generated response
        """
        system_prompt = """You are a helpful financial information assistant. Answer user questions about companies, stocks, and financial information directly and accurately.

Guidelines:
1. Answer the user's question directly and concisely
2. Use your knowledge about companies, products, financial metrics, etc.
3. If you don't know something, say so clearly
4. Format your response clearly using markdown if helpful
5. Be accurate and factual
6. Focus on answering what was asked, not providing extra analysis"""

        # Build context section if available
        context_section = ""
        if context_messages:
            context_section = "\n\n## Conversation Context:\n"
            for msg in context_messages[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_section += f"{role.capitalize()}: {content}\n"

        user_prompt = f"""User Query: {original_query}

Company: {company_name}
Date: {trade_date}
{context_section}

Please answer the user's question directly. If this is about a company's products, business, financials, or stock information, provide a helpful answer based on your knowledge."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"I apologize, but I encountered an error while generating a response. Please try again later. Error: {str(e)}"
    
    def format_response(
        self,
        original_query: str,
        final_state: Dict[str, Any],
        aggregated_context: Optional[AggregatedContext] = None,
        is_multi_agent: bool = False,
        company_name: Optional[str] = None,
        trade_date: Optional[str] = None,
        context_messages: Optional[List[Dict[str, Any]]] = None,
        auto_fallback: bool = True
    ) -> str:
        """
        Main formatting method that determines single vs multi-agent and formats accordingly.
        Automatically triggers fallback LLM if no agent output is available.
        
        Args:
            original_query: The user's original question
            final_state: Final state dictionary with agent reports
            aggregated_context: Optional aggregated context (required for multi-agent)
            is_multi_agent: Whether this is a multi-agent scenario
            company_name: Company name for fallback LLM
            trade_date: Trade date for fallback LLM
            context_messages: Conversation context for fallback LLM
            auto_fallback: If True, automatically use LLM fallback when no output available
            
        Returns:
            Formatted response or fallback LLM response
        """
        if is_multi_agent and aggregated_context:
            # Multi-agent case: collect all agent outputs
            agent_outputs_map = {}
            
            # Map agent IDs to their reports in final_state
            agent_report_mapping = {
                "market_analyst": "market_report",
                "fundamentals_analyst": "fundamentals_report",
                "information_analyst": "information_report"
            }
            
            for agent_id, report_key in agent_report_mapping.items():
                if agent_id in aggregated_context.get_successful_agents():
                    # Try final_state first
                    report_text = final_state.get(report_key, "")
                    
                    # Fallback to aggregated_context if not in final_state
                    if not report_text or not report_text.strip():
                        if agent_id in aggregated_context.agent_outputs:
                            payload = aggregated_context.agent_outputs[agent_id].payload
                            if isinstance(payload, dict):
                                report_text = payload.get(report_key, "")
                    
                    if report_text and report_text.strip():
                        agent_outputs_map[agent_id] = report_text
            
            if agent_outputs_map:
                return self.format_multi_agent_response(
                    original_query=original_query,
                    aggregated_context=aggregated_context,
                    agent_outputs_map=agent_outputs_map
                )
            else:
                # No outputs found - trigger fallback LLM if enabled
                if auto_fallback and company_name and trade_date:
                    print(f"⚠️  No agent outputs available. Triggering fallback LLM response.")
                    return self.generate_fallback_response(
                        original_query=original_query,
                        company_name=company_name,
                        trade_date=trade_date,
                        context_messages=context_messages
                    )
                return "No agent outputs available for formatting."
        else:
            # Single-agent case: find which agent ran and format its output
            agent_type = None
            agent_output = None
            
            # Check final_state first
            if final_state.get("market_report"):
                agent_type = "market_analyst"
                agent_output = final_state["market_report"]
            elif final_state.get("fundamentals_report"):
                agent_type = "fundamentals_analyst"
                agent_output = final_state["fundamentals_report"]
            elif final_state.get("information_report"):
                agent_type = "information_analyst"
                agent_output = final_state["information_report"]
            
            # Fallback to aggregated_context if not found in final_state
            if (not agent_output or not agent_output.strip()) and aggregated_context:
                successful_agents = aggregated_context.get_successful_agents()
                
                for agent_id in successful_agents:
                    if agent_id == "market_analyst" and not agent_output:
                        agent_type = "market_analyst"
                        if agent_id in aggregated_context.agent_outputs:
                            payload = aggregated_context.agent_outputs[agent_id].payload
                            if isinstance(payload, dict):
                                agent_output = payload.get("market_report", "")
                    elif agent_id == "fundamentals_analyst" and not agent_output:
                        agent_type = "fundamentals_analyst"
                        if agent_id in aggregated_context.agent_outputs:
                            payload = aggregated_context.agent_outputs[agent_id].payload
                            if isinstance(payload, dict):
                                agent_output = payload.get("fundamentals_report", "")
                    elif agent_id == "information_analyst" and not agent_output:
                        agent_type = "information_analyst"
                        if agent_id in aggregated_context.agent_outputs:
                            payload = aggregated_context.agent_outputs[agent_id].payload
                            if isinstance(payload, dict):
                                agent_output = payload.get("information_report", "")
            
            if agent_output and agent_output.strip():
                return self.format_single_agent_response(
                    original_query=original_query,
                    agent_output=agent_output,
                    agent_type=agent_type
                )
            else:
                # No agent output found - trigger fallback LLM immediately
                if auto_fallback and company_name and trade_date:
                    print(f"⚠️  No agent output available. Triggering fallback LLM response for: '{original_query}'")
                    return self.generate_fallback_response(
                        original_query=original_query,
                        company_name=company_name,
                        trade_date=trade_date,
                        context_messages=context_messages
                    )
                return "No agent output available for formatting."

