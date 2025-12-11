"""
Streaming utilities for agent execution.
Provides event emission and formatting for SSE.
"""
import datetime
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from collections import deque


class AgentStreamEvent:
    """Represents an agent streaming event."""
    
    def __init__(
        self,
        event_type: str,
        message: str,
        agent_name: Optional[str] = None,
        progress: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        self.event_type = event_type
        self.message = message
        self.agent_name = agent_name
        self.progress = progress
        self.data = data or {}
        self.timestamp = datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        result = {
            "event_type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp
        }
        
        if self.agent_name:
            result["agent_name"] = self.agent_name
        if self.progress is not None:
            result["progress"] = self.progress
        if self.data:
            result["data"] = self.data
        
        return result


class EventEmitter:
    """Event emitter for agent execution progress."""
    
    def __init__(self):
        self.events: deque = deque()
        self.callbacks: list[Callable[[AgentStreamEvent], None]] = []
        self.total_steps = 0
        self.current_step = 0
    
    def emit(self, event: AgentStreamEvent):
        """Emit an event to all registered callbacks."""
        self.events.append(event)
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                # Don't let callback errors break execution
                import logging
                logging.error(f"Event callback error: {e}")
    
    def on(self, callback: Callable[[AgentStreamEvent], None]):
        """Register an event callback."""
        self.callbacks.append(callback)
    
    def set_total_steps(self, total: int):
        """Set total number of steps for progress calculation."""
        self.total_steps = total
    
    def increment_step(self):
        """Increment current step and calculate progress."""
        self.current_step += 1
        if self.total_steps > 0:
            progress = int((self.current_step / self.total_steps) * 100)
            return min(progress, 100)
        return None


# Agent name mapping from graph node names
AGENT_NAME_MAP = {
    "market": "Market Analyst",
    "information": "Information Analyst",
    "fundamentals": "Fundamentals Analyst",
    "bull_researcher": "Bull Researcher",
    "bear_researcher": "Bear Researcher",
    "research_manager": "Research Manager",
    "trader": "Trader",
    "risky_analyst": "Risky Analyst",
    "neutral_analyst": "Neutral Analyst",
    "safe_analyst": "Safe Analyst",
    "risk_judge": "Risk Manager",
}


def get_agent_name(node_name: str) -> str:
    """Get human-readable agent name from graph node name."""
    return AGENT_NAME_MAP.get(node_name, node_name.replace("_", " ").title())


def detect_agent_from_state(state: Dict[str, Any]) -> Optional[str]:
    """Detect which agent is active from graph state."""
    # Check for analyst reports
    if state.get("market_report") and not state.get("fundamentals_report"):
        return "Market Analyst"
    if state.get("fundamentals_report"):
        return "Fundamentals Analyst"
    if state.get("sentiment_report") or state.get("news_report"):
        return "Information Analyst"
    
    # Check debate states
    debate_state = state.get("investment_debate_state", {})
    if isinstance(debate_state, dict):
        if debate_state.get("bull_history"):
            return "Bull Researcher"
        if debate_state.get("bear_history"):
            return "Bear Researcher"
        if debate_state.get("judge_decision"):
            return "Research Manager"
    
    risk_state = state.get("risk_debate_state", {})
    if isinstance(risk_state, dict):
        if risk_state.get("risky_history"):
            return "Risky Analyst"
        if risk_state.get("safe_history"):
            return "Safe Analyst"
        if risk_state.get("neutral_history"):
            return "Neutral Analyst"
        if risk_state.get("judge_decision"):
            return "Risk Manager"
    
    if state.get("trader_investment_plan"):
        return "Trader"
    
    return None

