# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date
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
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
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

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict
        
        # Store selected analysts for streaming
        self.selected_analysts = selected_analysts
        
        # Streaming support
        self.event_emitter: Optional[EventEmitter] = None
        self.enable_streaming = False

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)
    
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

    async def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date (async)."""

        self.ticker = company_name

        # Emit start event if streaming enabled
        if self.enable_streaming and self.event_emitter:
            start_event = AgentStreamEvent(
                event_type="analysis_start",
                message=f"Starting analysis for {company_name}",
                data={
                    "company": company_name,
                    "trade_date": str(trade_date),
                    "agents_selected": self.selected_analysts
                }
            )
            self.event_emitter.emit(start_event)

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
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

        # Return decision and processed signal
        return final_state, self.process_signal(final_state.get("final_trade_decision", "HOLD"))

    def _prepare_serializable_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare state for JSON serialization by removing non-serializable objects.
        Keeps all string reports and debate states.
        """
        serializable = {}
        
        # Include all string reports
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
            if field in state and isinstance(state[field], str):
                serializable[field] = state[field]
        
        # Include debate states (they contain string histories)
        if "investment_debate_state" in state:
            debate_state = state["investment_debate_state"]
            serializable["investment_debate_state"] = {
                "bull_history": debate_state.get("bull_history", ""),
                "bear_history": debate_state.get("bear_history", ""),
                "judge_decision": debate_state.get("judge_decision", "")
            }
        
        if "risk_debate_state" in state:
            risk_state = state["risk_debate_state"]
            serializable["risk_debate_state"] = {
                "risky_history": risk_state.get("risky_history", ""),
                "safe_history": risk_state.get("safe_history", ""),
                "neutral_history": risk_state.get("neutral_history", ""),
                "judge_decision": risk_state.get("judge_decision", "")
            }
        
        return serializable
    
    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
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
