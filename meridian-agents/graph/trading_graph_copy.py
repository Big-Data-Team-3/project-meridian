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
        selected_analysts=["market", "information", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
        include_debate: bool = True,
        include_risk: bool = True,
        planner: Optional[PlannerAgent] = None,
        use_dynamic_graph: bool = True,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include (legacy - used only if use_dynamic_graph=False)
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            include_debate: Whether to include research debate phase (legacy - used only if use_dynamic_graph=False)
            include_risk: Whether to include risk analysis phase (legacy - used only if use_dynamic_graph=False)
            planner: Optional PlannerAgent instance. If None and use_dynamic_graph=True, creates default planner
            use_dynamic_graph: If True, use dynamic graph construction (requires planner). If False, use legacy static graph.
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.use_dynamic_graph = use_dynamic_graph

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

        # Initialize planner if using dynamic graphs
        if use_dynamic_graph:
            if planner is None:
                # Create default planner
                self.planner = PlannerAgent()
            else:
                self.planner = planner
        else:
            self.planner = None

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict
        
        # Store selected analysts and workflow flags for streaming (legacy support)
        self.selected_analysts = selected_analysts
        self.include_debate = include_debate
        self.include_risk = include_risk
        
        # Streaming support
        self.event_emitter: Optional[EventEmitter] = None
        self.enable_streaming = False

        # Graph is now constructed dynamically at runtime (not in __init__)
        # Only create static graph if legacy mode is explicitly requested
        if not use_dynamic_graph:
            # Legacy mode: create static graph at initialization
            self.graph = self.graph_setup.setup_graph_legacy(
            selected_analysts=selected_analysts,
            include_debate=include_debate,
            include_risk=include_risk
        )
        else:
            # Dynamic mode: graph will be constructed in propagate()
            self.graph = None
            self.current_execution_plan: Optional[ExecutionPlan] = None
    
    def enable_event_streaming(self, event_emitter: Optional[EventEmitter] = None):
        """Enable event streaming for agent execution."""
        if EventEmitter is None:
            return  # Streaming not available
        
        self.enable_streaming = True
        self.event_emitter = event_emitter or EventEmitter()
        
        # Estimate total steps based on selected analysts
        total_steps = len(self.selected_analysts) * 2  # Rough estimate
        # Add steps for debate and risk if they're part of the workflow
        # (This would be determined by the workflow config, but we estimate conservatively)
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
        
        Args:
            company_name: Company ticker/name
            trade_date: Trade date
            query: Optional user query for dynamic planning (required if use_dynamic_graph=True)
            context: Optional conversation context for multi-turn conversations
            
        Returns:
            Tuple of (final_state, decision)
        """
        self.ticker = company_name

        # Dynamic graph construction: get execution plan from planner
        execution_plan: Optional[ExecutionPlan] = None
        has_debate = self.include_debate
        has_risk = self.include_risk
        
        if self.use_dynamic_graph:
            # CRITICAL: Always clear graph at start of each query to prevent reuse
            # This ensures each query gets a fresh graph based on its specific execution plan
            self.graph = None
            self.current_execution_plan = None
            
            if not query:
                # Generate default query from company name
                query = f"Analyze {company_name} for trading decision as of {trade_date}"
            
            try:
                execution_plan = self.planner.plan_workflow(query, context)
                self.current_execution_plan = execution_plan
                
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
                
            except Exception as e:
                print(f"⚠️  Planner failed: {str(e)}. Attempting intelligent fallback based on query.")
                # Intelligent fallback: try to infer single agent from query keywords
                execution_plan = None
                
                # Try to infer agent from query keywords
                query_lower = query.lower() if query else ""
                inferred_agent = None
                
                if any(keyword in query_lower for keyword in ["news", "sentiment", "social media", "announcements", "buzz", "trending"]):
                    # News/sentiment query - use only information_analyst
                    inferred_agent = "information"
                    print(f"📰 Detected news/sentiment query, using only information_analyst")
                elif any(keyword in query_lower for keyword in ["technical", "chart", "indicator", "rsi", "macd", "trend", "moving average"]):
                    # Technical query - use only market_analyst
                    inferred_agent = "market"
                    print(f"📈 Detected technical query, using only market_analyst")
                elif any(keyword in query_lower for keyword in ["fundamental", "financial", "earnings", "balance sheet", "p/e ratio", "valuation"]):
                    # Fundamental query - use only fundamentals_analyst
                    inferred_agent = "fundamentals"
                    print(f"💰 Detected fundamental query, using only fundamentals_analyst")
                
                if inferred_agent:
                    # Create minimal execution plan for single agent
                    from .planner.models import ExecutionPlan
                    execution_plan = ExecutionPlan(
                        agents=[f"{inferred_agent}_analyst"],
                        execution_order=[f"{inferred_agent}_analyst"],
                        criticality_map={f"{inferred_agent}_analyst": "critical"},
                        termination_conditions={},
                        reasoning=f"Fallback plan: detected {inferred_agent} query from keywords",
                        estimated_duration=45.0,
                        estimated_cost=0.05
                    )
                    self.current_execution_plan = execution_plan
                    self.graph = self.graph_setup.setup_graph(execution_plan, validate=True)
                    has_debate = False
                    has_risk = False
                    self.selected_analysts = [f"{inferred_agent}_analyst"]
                else:
                    # No keyword match - fall back to legacy (but warn)
                    print(f"⚠️  No keyword match found, falling back to legacy full graph")
                    execution_plan = None
                    self.graph = self.graph_setup.setup_graph_legacy(
                        selected_analysts=self.selected_analysts,
                        include_debate=self.include_debate,
                        include_risk=self.include_risk
                    )
                    has_debate = self.include_debate
                    has_risk = self.include_risk
        else:
            # Legacy mode: use existing static graph
            execution_plan = None

        # Emit start event if streaming enabled
        if self.enable_streaming and self.event_emitter:
            agents_info = execution_plan.agents if execution_plan else self.selected_analysts
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

        # Emit completion event if streaming enabled
        if self.enable_streaming and self.event_emitter:
            decision = self.process_signal(final_state.get("final_trade_decision", "HOLD"))
            
            # Prepare serializable state (remove non-serializable objects)
            serializable_state = self._prepare_serializable_state(final_state)
            
            complete_event = AgentStreamEvent(
                event_type="analysis_complete",
                message=f"Analysis complete for {company_name}",
                progress=100,
                data={
                    "decision": decision,
                    "company": company_name,
                    "date": str(trade_date),
                    "state": serializable_state,  # Include full state for frontend breakdown
                    "response": (
                        final_state.get("final_trade_decision") or
                        final_state.get("trader_investment_plan") or
                        final_state.get("investment_plan") or
                        decision
                    )
                }
            )
            self.event_emitter.emit(complete_event)

        # Log state
        self._log_state(trade_date, final_state)

        # Extract decision - for single-agent queries without trader/risk, use report content
        # or default to "HOLD" if no explicit decision found
        decision = "HOLD"
        # Use execution plan to determine workflow structure if available
        # (has_risk and has_debate are already set above)
        
        if has_risk and final_state.get("final_trade_decision"):
            # Full workflow - use risk manager's decision
            decision = self.process_signal(final_state.get("final_trade_decision"))
        elif has_debate and final_state.get("trader_investment_plan"):
            # Has trader but no risk - use trader's plan
            decision = self.process_signal(final_state.get("trader_investment_plan"))
        elif final_state.get("final_trade_decision"):
            # Fallback to any decision found
            decision = self.process_signal(final_state.get("final_trade_decision"))
        else:
            # Single-agent query - try to extract from market report or use default
            market_report = final_state.get("market_report", "")
            if "FINAL TRANSACTION PROPOSAL:" in market_report:
                # Extract decision from market report if present
                decision = self.process_signal(market_report)
            else:
                # No explicit decision - use "HOLD" as default
                decision = "HOLD"

        # Synthesize final answer from aggregated context (if available)
        synthesizer_output = None
        if aggregated_context and len(aggregated_context.agent_outputs) > 0:
            try:
                synthesizer_output = self.synthesizer.synthesize(
                    aggregated_context=aggregated_context,
                    original_query=query
                )
                # Use synthesizer recommendation if available
                if synthesizer_output.recommendation:
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
            "final_trade_decision"
        ]
        
        for field in string_fields:
            if field in state and isinstance(state[field], str) and state[field].strip():
                serializable[field] = state[field]
        
        # Only include debate state if debate phase was actually used
        has_debate = (self.current_execution_plan and any(agent_id in ["bull_researcher", "bear_researcher", "research_manager"] 
                                                          for agent_id in self.current_execution_plan.agents)) or self.include_debate
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
                                                      for agent_id in self.current_execution_plan.agents)) or self.include_risk
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
