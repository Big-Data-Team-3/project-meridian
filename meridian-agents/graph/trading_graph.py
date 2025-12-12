# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date, datetime
from typing import Dict, Any, Tuple, List, Optional, Callable

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from agents_module import *
from default_config import DEFAULT_CONFIG
from agents_module.utils.memory import FinancialSituationMemory
from agents_module.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from dataflows.config import set_config

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor
from .planner import PlannerAgent
from .planner.models import ExecutionPlan
from .orchestrator import Orchestrator
from .orchestrator.models import AggregatedContext
from .synthesizer import FinalSynthesizer
from .synthesizer.models import SynthesizerOutput
from .response_formatter import ResponseFormatter

# Import streaming utilities
try:
    from utils.streaming import EventEmitter, AgentStreamEvent, get_agent_name, detect_agent_from_state
except ImportError:
    # Fallback if streaming utils not available
    EventEmitter = None
    AgentStreamEvent = None
    get_agent_name = lambda x: x
    detect_agent_from_state = lambda x: None


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        debug=False,
        config: Dict[str, Any] = None,
        planner: Optional[PlannerAgent] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            planner: Optional PlannerAgent instance. If None, creates default planner
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai" or self.config["llm_provider"] == "ollama" or self.config["llm_provider"] == "openrouter":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.config,  # Pass config instead of tool_nodes
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)
        self.orchestrator = Orchestrator()
        self.synthesizer = FinalSynthesizer()

        # Initialize planner (always required for dynamic graphs)
        if planner is None:
            # Create default planner
            self.planner = PlannerAgent()
        else:
            self.planner = planner

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict
        
        # Streaming support
        self.event_emitter: Optional[EventEmitter] = None
        self.enable_streaming = False

        # Graph is always constructed dynamically at runtime in propagate()
        self.graph = None
        self.current_execution_plan: Optional[ExecutionPlan] = None
        self.selected_analysts = []  # Will be set from execution plan
    
    def enable_event_streaming(self, event_emitter: Optional[EventEmitter] = None):
        """Enable event streaming for agent execution."""
        if EventEmitter is None:
            return  # Streaming not available
        
        self.enable_streaming = True
        self.event_emitter = event_emitter or EventEmitter()
        
        # Estimate total steps based on selected analysts
        # Note: selected_analysts will be set from execution plan during propagate()
        # Use a conservative estimate for now
        total_steps = max(len(self.selected_analysts) * 2, 10)  # Minimum 10 steps
        # Add steps for debate and risk (conservative estimate)
        total_steps += 4  # Potential debate steps
        total_steps += 3  # Potential risk steps
        
        self.event_emitter.set_total_steps(total_steps)

    async def propagate(
        self, 
        company_name: str, 
        trade_date: str,
        query: Optional[str] = None,
        context: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Run the trading agents graph for a company on a specific date (async).
        
        The graph is always constructed dynamically based on the query and execution plan.
        No static/legacy graphs are used.
        
        Args:
            company_name: Company ticker/name
            trade_date: Trade date
            query: User query for dynamic planning (required - will be generated from company_name if not provided)
            context: Optional conversation context for multi-turn conversations
            
        Returns:
            Tuple of (final_state, decision, aggregated_context, synthesizer_output)
        """
        self.ticker = company_name

        # Dynamic graph construction: get execution plan from planner
        # CRITICAL: Always clear graph at start of each query to prevent reuse
        # This ensures each query gets a fresh graph based on its specific execution plan
        self.graph = None
        self.current_execution_plan = None
        # CRITICAL: Clear selected_analysts to prevent using stale values from previous queries
        self.selected_analysts = []
        execution_plan: Optional[ExecutionPlan] = None
        
        if not query:
            # Generate default query from company name
            query = f"Analyze {company_name} for trading decision as of {trade_date}"
            print(f"⚠️ WARNING: propagate() received query=None! Generated default: '{query}'")
        else:
            print(f"📥 propagate() received query: '{query[:200]}...'")
        
        # PRIMARY: Try LLM Planner first for intelligent reasoning-based planning
        # This allows the LLM to analyze the query and generate sophisticated execution plans
        execution_plan = None
        has_debate = False
        has_risk = False
        
        try:
            print(f"🤖 Calling LLM Planner for query: '{query[:200]}...'")
            execution_plan = self.planner.plan_workflow(query, context)
            self.current_execution_plan = execution_plan
            print(f"📋 Planner returned execution plan with {len(execution_plan.agents)} agents: {execution_plan.agents}")
            if execution_plan.reasoning:
                print(f"💭 Planner reasoning: {execution_plan.reasoning[:200]}...")
            
            # Construct graph dynamically based on execution plan
            self.graph = self.graph_setup.setup_graph(execution_plan, validate=True)
            
            # Determine workflow flags from execution plan for state initialization
            has_debate = any(agent_id in ["bull_researcher", "bear_researcher", "research_manager"] 
                            for agent_id in execution_plan.agents)
            has_risk = any(agent_id in ["risky_debator", "safe_debator", "neutral_debator", "risk_manager"]
                          for agent_id in execution_plan.agents)
            
            # Update selected analysts for streaming
            self.selected_analysts = [agent_id for agent_id in execution_plan.agents 
                                     if agent_id in ["market_analyst", "fundamentals_analyst", "information_analyst"]]
            print(f"✅ LLM Planner SUCCESS: Created execution plan with {len(execution_plan.agents)} agents")
        
        except Exception as e:
            # FALLBACK: Planner failed - use pre-filter keyword matching
            print(f"❌ Planner failed: {str(e)}. Falling back to pre-filter keyword matching.")
            
            # Pre-filter: Detect simple single-agent queries based on keywords
            # Normalize query: strip whitespace and convert to lowercase for reliable matching
            query_normalized = query.strip().lower() if query else ""
            inferred_agent = None
            
            # News/sentiment keywords (highest priority - check first)
            news_keywords = ["news", "sentiment", "social media", "announcements", "buzz", "trending", "latest news", "what's the news", "recent news", "what is the news"]
            if any(keyword in query_normalized for keyword in news_keywords):
                inferred_agent = "information"
                matched_keyword = next((kw for kw in news_keywords if kw in query_normalized), "news")
                print(f"📰 Pre-filter fallback: detected news/sentiment query (matched: '{matched_keyword}'), using ONLY information_analyst")
            
            # Technical keywords
            elif any(keyword in query_normalized for keyword in ["technical", "chart", "indicator", "rsi", "macd", "trend", "moving average", "technical analysis"]):
                inferred_agent = "market"
                matched_keyword = next((kw for kw in ["technical", "chart", "indicator", "rsi", "macd", "trend", "moving average", "technical analysis"] if kw in query_normalized), "technical")
                print(f"📈 Pre-filter fallback: detected technical query (matched: '{matched_keyword}'), using ONLY market_analyst")
            
            # Fundamental keywords
            elif any(keyword in query_normalized for keyword in ["fundamental", "financial", "earnings", "balance sheet", "p/e ratio", "valuation", "financials"]):
                inferred_agent = "fundamentals"
                matched_keyword = next((kw for kw in ["fundamental", "financial", "earnings", "balance sheet", "p/e ratio", "valuation", "financials"] if kw in query_normalized), "fundamental")
                print(f"💰 Pre-filter fallback: detected fundamental query (matched: '{matched_keyword}'), using ONLY fundamentals_analyst")
            
            # Company information keywords (catch-all for general company queries)
            elif any(keyword in query_normalized for keyword in ["products", "business", "what does", "tell me about", "what is", "main products", "business model", "what are", "company"]):
                inferred_agent = "information"
                matched_keyword = next((kw for kw in ["products", "business", "what does", "tell me about", "what is", "main products", "business model", "what are", "company"] if kw in query_normalized), "company info")
                print(f"ℹ️ Pre-filter fallback: detected company information query (matched: '{matched_keyword}'), using ONLY information_analyst")
            
            # Final fallback: if query mentions a company/ticker but no specific keywords matched, use information_analyst
            elif company_name and company_name.lower() in query_normalized:
                inferred_agent = "information"
                print(f"ℹ️ Pre-filter fallback: detected company mention in query, defaulting to information_analyst")
            
            if inferred_agent:
                # Create execution plan using pre-filter fallback
                from .planner.models import ExecutionPlan
                agent_id = f"{inferred_agent}_analyst"
                execution_plan = ExecutionPlan(
                    agents=[agent_id],
                    execution_order=[agent_id],
                    criticality_map={agent_id: "critical"},
                    termination_conditions={},
                    reasoning=f"Pre-filter fallback: detected {inferred_agent} query from keywords - using single agent only",
                    estimated_duration=45.0,
                    estimated_cost=0.05
                )
                self.current_execution_plan = execution_plan
                self.graph = self.graph_setup.setup_graph(execution_plan, validate=True)
                has_debate = False
                has_risk = False
                self.selected_analysts = [agent_id]
                print(f"✅ Pre-filter fallback SUCCESS: Created execution plan with single agent: {agent_id}")
            else:
                # No keyword match - raise error
                raise ValueError(
                    f"Planner failed and pre-filter fallback could not infer agent from query keywords. "
                    f"Query: '{query}'. Please ensure planner is working or provide a more specific query."
                )

        # Emit start event if streaming enabled
        if self.enable_streaming and self.event_emitter:
            # CRITICAL: Always use execution_plan.agents if available, never fall back to selected_analysts
            # This ensures we show the actual agents that will run, not a cached/stale list
            if execution_plan:
                agents_info = execution_plan.agents
                print(f"📊 Emitting start event with {len(agents_info)} agents from execution_plan: {agents_info}")
            else:
                # This should never happen if code flow is correct, but log it for debugging
                agents_info = self.selected_analysts if self.selected_analysts else []
                print(f"⚠️ WARNING: execution_plan is None! Using selected_analysts fallback: {agents_info}")
            
            start_event = AgentStreamEvent(
                event_type="analysis_start",
                message=f"Starting analysis for {company_name}",
                data={
                    "company": company_name,
                    "trade_date": str(trade_date),
                    "agents_selected": agents_info,
                    "execution_plan": execution_plan.model_dump() if execution_plan else None
                }
            )
            self.event_emitter.emit(start_event)

        # Initialize state with workflow flags
        init_agent_state = self.propagator.create_initial_state(
            company_name, 
            trade_date,
            include_debate=has_debate,
            include_risk=has_risk
        )
        args = self.propagator.get_graph_args()

        # Run graph execution in thread pool to avoid event loop conflicts
        import asyncio
        
        def _run_graph():
            """Run graph synchronously in thread pool."""
            if self.enable_streaming or self.debug:
                # Use streaming mode to track progress
                trace = []
                previous_agent = None
                
                for chunk in self.graph.stream(init_agent_state, **args):
                    # Extract state from chunk
                    state = chunk if isinstance(chunk, dict) else chunk.get("state", {}) if hasattr(chunk, "get") else {}
                    
                    # Detect current agent
                    current_agent = detect_agent_from_state(state)
                    
                    # Check for tool calls in messages
                    messages = chunk.get("messages", [])
                    tool_calls_detected = []
                    for msg in messages:
                        # Check for tool calls in LangChain message format
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                tool_calls_detected.append({
                                    "name": tool_call.get("name", "unknown"),
                                    "args": tool_call.get("args", {})
                                })
                        # Also check for ToolMessage (result of tool execution)
                        elif hasattr(msg, "content") and hasattr(msg, "name") and msg.name:
                            # ToolMessage typically has a name attribute
                            if "tool" in str(type(msg)).lower() or "ToolMessage" in str(type(msg)):
                                tool_calls_detected.append({
                                    "name": getattr(msg, "name", "unknown"),
                                    "result": str(msg.content)[:100] if hasattr(msg, "content") else ""
                                })
                    
                    # Emit agent activity events
                    if self.enable_streaming and self.event_emitter:
                        if current_agent and current_agent != previous_agent:
                            # New agent started
                            agent_event = AgentStreamEvent(
                                event_type="agent_active",
                                agent_name=current_agent,
                                message=f"{current_agent} is now analyzing {company_name}",
                                progress=self.event_emitter.increment_step()
                            )
                            self.event_emitter.emit(agent_event)
                            previous_agent = current_agent
                        
                        # Emit tool usage events
                        if tool_calls_detected:
                            for tool_call in tool_calls_detected:
                                tool_event = AgentStreamEvent(
                                    event_type="tool_usage",
                                    agent_name=current_agent or "Unknown",
                                    message=f"Using tool: {tool_call.get('name', 'unknown')}",
                                    data={"tool_name": tool_call.get("name"), "tool_args": tool_call.get("args")}
                                )
                                self.event_emitter.emit(tool_event)
                        
                        if current_agent:
                            # Same agent, progress update
                            progress = self.event_emitter.increment_step()
                            if progress and progress % 10 == 0:  # Emit every 10%
                                progress_event = AgentStreamEvent(
                                    event_type="progress",
                                    agent_name=current_agent,
                                    message=f"{current_agent} is analyzing...",
                                    progress=progress
                                )
                                self.event_emitter.emit(progress_event)
                    
                    if self.debug:
                        if len(chunk.get("messages", [])) > 0:
                            chunk["messages"][-1].pretty_print()
                    
                    trace.append(chunk)
                
                # Get final state from last chunk
                final_state = trace[-1] if trace else self.graph.invoke(init_agent_state, **args)
                return final_state
            else:
                # Standard mode without tracing
                return self.graph.invoke(init_agent_state, **args)

        # Run in thread pool to avoid event loop conflicts
        final_state = await asyncio.to_thread(_run_graph)

        # Store current state for reflection
        self.curr_state = final_state
        
        # Aggregate results using orchestrator (if execution plan available)
        aggregated_context = None
        if execution_plan:
            workflow_start_time = datetime.utcnow()
            
            aggregated_context = self.orchestrator.aggregate_results(
                final_state=final_state,
                execution_plan=execution_plan,
                workflow_start_time=workflow_start_time,
                execution_trace=None  # Could pass trace if needed
            )
            
            # If workflow was aborted due to critical failure, handle it
            if aggregated_context.workflow_aborted:
                print(f"⚠️  Workflow aborted at critical agent: {aggregated_context.aborted_at_agent}")
                if self.enable_streaming and self.event_emitter:
                    abort_event = AgentStreamEvent(
                        event_type="workflow_aborted",
                        message=f"Workflow aborted: Critical agent {aggregated_context.aborted_at_agent} failed",
                        data={
                            "aborted_at_agent": aggregated_context.aborted_at_agent,
                            "critical_failures": aggregated_context.get_critical_failures(),
                            "partial_results_available": aggregated_context.partial_results_available
                        }
                    )
                    self.event_emitter.emit(abort_event)

        # Detect if this is a news-only query (before decision extraction)
        is_news_only = False
        if query:
            query_lower = query.lower()
            news_keywords = ["news", "sentiment", "summarize", "what's the news", "latest news", "recent news"]
            trading_keywords = ["should i", "buy", "sell", "trade", "investment", "recommendation", "decision"]
            has_news_keyword = any(kw in query_lower for kw in news_keywords)
            has_trading_keyword = any(kw in query_lower for kw in trading_keywords)
            
            # Check execution plan - if only information_analyst, it's news-only
            if execution_plan and len(execution_plan.agents) == 1 and "information_analyst" in execution_plan.agents:
                is_news_only = True
            elif has_news_keyword and not has_trading_keyword:
                is_news_only = True

            # Determine if this query requires a trading decision
            # ONLY set decision when the actual static workflow (with debate/risk phases) is orchestrated
        requires_decision = has_debate or has_risk
                
                # Apply response formatting for non-workflow queries (single-agent or multi-agent)
        # This runs for BOTH streaming and non-streaming endpoints
        # Formatting applies to simple analysis queries (no debate/risk workflow) and news-only queries
        if query and not requires_decision:
                    try:
                        formatter = ResponseFormatter()
                        
                        # Determine if this is multi-agent (multiple analysts but no debate/risk)
                        analyst_agents = [agent_id for agent_id in (execution_plan.agents if execution_plan else [])
                                          if agent_id in ["market_analyst", "fundamentals_analyst", "information_analyst"]]
                        is_multi_agent = len(analyst_agents) > 1
                        
                # Emit event before formatting (only if streaming enabled)
                        if self.enable_streaming and self.event_emitter:
                            format_start_event = AgentStreamEvent(
                                event_type="formatting_start",
                                message="Formatting response based on agent output",
                                data={"query": query, "company": company_name}
                            )
                            self.event_emitter.emit(format_start_event)
                        
                        formatted_response = formatter.format_response(
                            original_query=query,
                            final_state=final_state,
                            aggregated_context=aggregated_context,
                            is_multi_agent=is_multi_agent,
                            company_name=company_name,
                            trade_date=str(trade_date),
                            context_messages=context,
                            auto_fallback=True
                        )
                        
                        # Check if fallback was used by checking if we have agent output available
                        # Check both final_state and aggregated_context
                        has_agent_output_in_state = (
                            final_state.get("market_report") or
                            final_state.get("fundamentals_report") or
                            final_state.get("information_report")
                        )
                        
                        # Also check aggregated_context
                        has_agent_output_in_context = False
                        if aggregated_context:
                            for agent_id in ["market_analyst", "fundamentals_analyst", "information_analyst"]:
                                if agent_id in aggregated_context.get_successful_agents():
                                    has_agent_output_in_context = True
                                    break
                        
                        has_agent_output = has_agent_output_in_state or has_agent_output_in_context
                        
                        # If no agent output available but we got a response (not error message), it's from fallback LLM
                        used_fallback = (
                            not has_agent_output and 
                            formatted_response and 
                            "No agent output available" not in formatted_response and
                            "No agent outputs available" not in formatted_response
                        )
                        
                # Emit fallback event (only if streaming enabled)
                        if used_fallback and self.enable_streaming and self.event_emitter:
                            fallback_event = AgentStreamEvent(
                                event_type="fallback_llm_used",
                                message="Using fallback LLM response (agent output not available)",
                                data={
                                    "query": query,
                                    "company": company_name,
                                    "date": str(trade_date),
                                    "response_length": len(formatted_response)
                                }
                            )
                            self.event_emitter.emit(fallback_event)
                        
                # Store formatted response in state (for both streaming and non-streaming)
                        final_state["formatted_response"] = formatted_response
                        final_state["response_source"] = "fallback_llm" if used_fallback else "formatted_agent_output"
                        
                        print(f"✅ Response ready (source: {final_state['response_source']}): '{query[:100]}...'")
                    except Exception as e:
                        print(f"⚠️  Response formatting failed: {str(e)}. Using original report.")
                # Don't set formatted_response if formatting failed

        # Emit completion event if streaming enabled
        if self.enable_streaming and self.event_emitter:
            # For news-only or simple analysis queries (no debate/risk phases), don't extract a decision
            if is_news_only or not requires_decision:
                streaming_decision = None
                
                # Use formatted response if available (from formatting above), otherwise fall back to original reports
                if final_state.get("formatted_response"):
                    streaming_response = final_state["formatted_response"]
                else:
                    # Fallback to original behavior if formatting didn't run or failed
                    if is_news_only:
                        streaming_response = (
                            final_state.get("information_report") or
                            final_state.get("news_report") or
                            final_state.get("sentiment_report") or
                            "News summary not available"
                        )
                    else:
                        # Simple analysis query - use the relevant analyst report
                        streaming_response = (
                            final_state.get("market_report") or
                            final_state.get("fundamentals_report") or
                            final_state.get("information_report") or
                            "Analysis report not available"
                        )
            else:
                # Full workflow - extract decision from workflow outputs
                streaming_decision = None
                if has_risk and final_state.get("final_trade_decision"):
                    streaming_decision = self.process_signal(final_state.get("final_trade_decision"))
                elif has_debate and final_state.get("trader_investment_plan"):
                    streaming_decision = self.process_signal(final_state.get("trader_investment_plan"))
                elif final_state.get("final_trade_decision"):
                    streaming_decision = self.process_signal(final_state.get("final_trade_decision"))
                
                # Use workflow outputs as response
                streaming_response = (
                    final_state.get("final_trade_decision") or
                    final_state.get("trader_investment_plan") or
                    final_state.get("investment_plan") or
                    (streaming_decision if streaming_decision else "Workflow analysis complete")
                )
            
            # Prepare serializable state (remove non-serializable objects)
            serializable_state = self._prepare_serializable_state(final_state)
            
            complete_event = AgentStreamEvent(
                event_type="analysis_complete",
                message=f"Analysis complete for {company_name}",
                progress=100,
                data={
                    "decision": streaming_decision,
                    "company": company_name,
                    "date": str(trade_date),
                    "state": serializable_state,  # Include full state for frontend breakdown
                    "response": streaming_response
                }
            )
            self.event_emitter.emit(complete_event)

        # Log state
        self._log_state(trade_date, final_state)

        # Determine if this query requires a trading decision
        # ONLY set decision when the actual static workflow (with debate/risk phases) is orchestrated
        # Decision should be None for simple single-agent queries, regardless of query keywords
        requires_decision = has_debate or has_risk
        
        # For news-only or simple analysis queries (no debate/risk phases), don't extract a trading decision
        if is_news_only or not requires_decision:
            decision = None  # No trading decision for simple analysis queries
            if is_news_only:
                print(f"📰 News-only query detected - skipping trading decision extraction")
            else:
                print(f"📊 Simple analysis query detected (no debate/risk workflow) - skipping trading decision extraction")
        else:
            # Trading decision query - ONLY when has_debate OR has_risk is True (full workflow orchestrated)
            # Extract decision from the workflow outputs
            decision = None  # Start with None, only set if we find an actual decision
            
            if has_risk and final_state.get("final_trade_decision"):
                # Full workflow with risk - use risk manager's decision
                decision = self.process_signal(final_state.get("final_trade_decision"))
            elif has_debate and final_state.get("trader_investment_plan"):
                # Has trader but no risk - use trader's plan
                decision = self.process_signal(final_state.get("trader_investment_plan"))
            elif final_state.get("final_trade_decision"):
                # Fallback to any decision found
                decision = self.process_signal(final_state.get("final_trade_decision"))
            
            # If no decision found in workflow outputs, keep it as None (don't default to HOLD)
            if decision is None:
                print(f"⚠️  Full workflow executed but no explicit decision found - returning None")

        # Synthesize final answer from aggregated context (if available)
        # ONLY use synthesizer for full workflow queries (has_debate or has_risk)
        synthesizer_output = None
        if requires_decision and aggregated_context and len(aggregated_context.agent_outputs) > 0:
            try:
                synthesizer_output = self.synthesizer.synthesize(
                    aggregated_context=aggregated_context,
                    original_query=query
                )
                # Use synthesizer recommendation if available (only for full workflow queries)
                if synthesizer_output.recommendation and not is_news_only:
                    decision = synthesizer_output.recommendation
            except Exception as e:
                print(f"⚠️  Synthesizer failed: {str(e)}. Using extracted decision.")

        # Return final state, decision, aggregated context, and synthesizer output
        return final_state, decision, aggregated_context, synthesizer_output

    def _prepare_serializable_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare state for JSON serialization by removing non-serializable objects.
        Only includes fields that have content and were actually used in the workflow.
        """
        serializable = {}
        
        # Include string reports (only if they have content)
        string_fields = [
            "market_report",
            "fundamentals_report", 
            "sentiment_report",
            "news_report",
            "information_report",
            "investment_plan",
            "trader_investment_plan",
            "final_trade_decision",
            "formatted_response",  # Query-aware formatted response from ResponseFormatter
            "response_source"       # Source of response (formatted_agent_output or fallback_llm)
        ]
        
        for field in string_fields:
            if field in state:
                # For formatted_response and response_source, include even if empty (for debugging)
                if field in ["formatted_response", "response_source"]:
                    if isinstance(state[field], str):
                        serializable[field] = state[field]
                elif isinstance(state[field], str) and state[field].strip():
                    serializable[field] = state[field] if isinstance(state[field], str) else str(state[field])
        
        # Only include debate state if debate phase was actually used
        has_debate = (self.current_execution_plan and any(agent_id in ["bull_researcher", "bear_researcher", "research_manager"] 
                                                          for agent_id in self.current_execution_plan.agents))
        if has_debate and "investment_debate_state" in state:
            debate_state = state["investment_debate_state"]
            # Only include if there's actual content
            has_debate_content = any([
                debate_state.get("bull_history", "").strip(),
                debate_state.get("bear_history", "").strip(),
                debate_state.get("judge_decision", "").strip()
            ])
            if has_debate_content:
                serializable["investment_debate_state"] = {
                    "bull_history": debate_state.get("bull_history", ""),
                    "bear_history": debate_state.get("bear_history", ""),
                    "judge_decision": debate_state.get("judge_decision", "")
                }
        
        # Only include risk state if risk phase was actually used
        has_risk = (self.current_execution_plan and any(agent_id in ["risky_debator", "safe_debator", "neutral_debator", "risk_manager"]
                                                      for agent_id in self.current_execution_plan.agents))
        if has_risk and "risk_debate_state" in state:
            risk_state = state["risk_debate_state"]
            # Only include if there's actual content
            has_risk_content = any([
                risk_state.get("risky_history", "").strip(),
                risk_state.get("safe_history", "").strip(),
                risk_state.get("neutral_history", "").strip(),
                risk_state.get("judge_decision", "").strip()
            ])
            if has_risk_content:
                serializable["risk_debate_state"] = {
                    "risky_history": risk_state.get("risky_history", ""),
                    "safe_history": risk_state.get("safe_history", ""),
                    "neutral_history": risk_state.get("neutral_history", ""),
                    "judge_decision": risk_state.get("judge_decision", "")
                }
        
        return serializable
    
    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        # Safely extract debate state fields with defaults
        investment_debate = final_state.get("investment_debate_state", {})
        risk_debate = final_state.get("risk_debate_state", {})
        
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state.get("company_of_interest", ""),
            "trade_date": final_state.get("trade_date", ""),
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "fundamentals_report": final_state.get("fundamentals_report", ""),
            "investment_debate_state": {
                "bull_history": investment_debate.get("bull_history", ""),
                "bear_history": investment_debate.get("bear_history", ""),
                "history": investment_debate.get("history", ""),
                "current_response": investment_debate.get("current_response", ""),
                "judge_decision": investment_debate.get("judge_decision", ""),
            },
            "trader_investment_decision": final_state.get("trader_investment_plan", ""),
            "risk_debate_state": {
                "risky_history": risk_debate.get("risky_history", ""),
                "safe_history": risk_debate.get("safe_history", ""),
                "neutral_history": risk_debate.get("neutral_history", ""),
                "history": risk_debate.get("history", ""),
                "judge_decision": risk_debate.get("judge_decision", ""),
            },
            "investment_plan": final_state.get("investment_plan", ""),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
