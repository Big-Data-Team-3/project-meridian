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
        # Use UTC timezone for consistent timestamps across systems
        self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
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
    """
    Detect which agent is active from graph state by checking what changed.
    This function is called on EACH chunk, so we detect based on the SENDER field
    or by checking which fields were just populated.
    """
    # Priority 1: Check for 'sender' field in state (most reliable)
    if "sender" in state and state["sender"]:
        sender = state["sender"]
        # Map sender names to display names
        sender_map = {
            "market_analyst": "Market Analyst",
            "fundamentals_analyst": "Fundamentals Analyst", 
            "information_analyst": "Information Analyst",
            "bull_researcher": "Bull Researcher",
            "bear_researcher": "Bear Researcher",
            "research_manager": "Research Manager",
            "trader": "Trader",
            "aggressive_debator": "Aggressive Risk Analyst",
            "conservative_debator": "Conservative Risk Analyst",
            "neutral_debator": "Neutral Risk Analyst",
            "risk_manager": "Risk Manager"
        }
        return sender_map.get(sender.lower().replace(" ", "_"), sender)
    
    # Priority 2: Check messages for agent identification
    messages = state.get("messages", [])
    if messages and len(messages) > 0:
        last_msg = messages[-1]
        if hasattr(last_msg, "name") and last_msg.name:
            name = last_msg.name.lower()
            if "market" in name:
                return "Market Analyst"
            elif "fundamental" in name:
                return "Fundamentals Analyst"
            elif "information" in name or "sentiment" in name:
                return "Information Analyst"
            elif "bull" in name:
                return "Bull Researcher"
            elif "bear" in name:
                return "Bear Researcher"
            elif "research" in name and "manager" in name:
                return "Research Manager"
            elif "trader" in name:
                return "Trader"
            elif "risk" in name and "manager" in name:
                return "Risk Manager"
            elif "aggressive" in name or "risky" in name:
                return "Aggressive Risk Analyst"
            elif "conservative" in name or "safe" in name:
                return "Conservative Risk Analyst"
            elif "neutral" in name:
                return "Neutral Risk Analyst"
    
    # Priority 3: Detect from state fields (less reliable, but fallback)
    # Check if this chunk has new content compared to what we expect
    # This is tricky because state is cumulative
    
    return None

