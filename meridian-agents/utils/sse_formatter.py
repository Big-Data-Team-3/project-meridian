"""
SSE (Server-Sent Events) formatting utilities.
Formats agent stream events for SSE transmission.
"""
import json
from typing import Dict, Any, List
from utils.streaming import AgentStreamEvent


def serialize_state_for_json(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize state dictionary, converting LangChain message objects to JSON-serializable format.
    
    Args:
        state: State dictionary that may contain LangChain message objects
        
    Returns:
        JSON-serializable dictionary
    """
    if not isinstance(state, dict):
        return str(state)
    
    serialized = {}
    for key, value in state.items():
        if value is None:
            continue
        elif isinstance(value, (str, int, float, bool)):
            serialized[key] = value
        elif isinstance(value, list):
            serialized[key] = [
                serialize_state_for_json(item) if isinstance(item, dict) 
                else serialize_message(item) if not isinstance(item, (str, int, float, bool, type(None)))
                else item
                for item in value
            ]
        elif isinstance(value, dict):
            serialized[key] = serialize_state_for_json(value)
        else:
            # Handle LangChain message objects and other non-serializable objects
            serialized[key] = serialize_message(value)
    
    return serialized


def serialize_message(msg: Any) -> Any:
    """
    Serialize a LangChain message object to a JSON-serializable format.
    
    Args:
        msg: LangChain message object (HumanMessage, AIMessage, etc.) or other object
        
    Returns:
        JSON-serializable representation
    """
    # Check if it's a LangChain message object
    if hasattr(msg, 'content'):
        result = {
            "type": type(msg).__name__,
            "content": str(msg.content) if msg.content else ""
        }
        # Add additional attributes if they exist
        if hasattr(msg, 'name') and msg.name:
            result["name"] = str(msg.name)
        if hasattr(msg, 'role'):
            result["role"] = str(msg.role)
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            result["tool_calls"] = [
                {
                    "name": str(tc.get("name", "")),
                    "args": tc.get("args", {})
                } if isinstance(tc, dict) else str(tc)
                for tc in msg.tool_calls
            ]
        return result
    elif hasattr(msg, '__dict__'):
        # Try to serialize as dict
        try:
            return {k: serialize_message(v) for k, v in msg.__dict__.items()}
        except:
            return str(msg)
    else:
        return str(msg)


def format_sse_event(event: AgentStreamEvent) -> str:
    """
    Format an AgentStreamEvent as SSE data line.
    
    Args:
        event: AgentStreamEvent instance
        
    Returns:
        SSE-formatted string: "data: {json}\n\n"
    """
    event_dict = event.to_dict()
    # Remove None values to keep payload clean
    event_dict = {k: v for k, v in event_dict.items() if v is not None}
    
    # Serialize any state data that might contain LangChain message objects
    if "data" in event_dict and isinstance(event_dict["data"], dict):
        if "state" in event_dict["data"]:
            event_dict["data"]["state"] = serialize_state_for_json(event_dict["data"]["state"])
        # Also serialize the entire data dict to catch any nested message objects
        event_dict["data"] = serialize_state_for_json(event_dict["data"])
    
    json_data = json.dumps(event_dict, default=str)  # Use default=str as fallback
    return f"data: {json_data}\n\n"


def format_sse_comment(comment: str) -> str:
    """
    Format a comment line for SSE (keeps connection alive).
    
    Args:
        comment: Comment text
        
    Returns:
        SSE comment line: ": {comment}\n"
    """
    return f": {comment}\n"

