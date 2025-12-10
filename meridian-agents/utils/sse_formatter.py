"""
SSE (Server-Sent Events) formatting utilities.
Formats agent stream events for SSE transmission.
"""
import json
from typing import Dict, Any
from utils.streaming import AgentStreamEvent


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
    
    json_data = json.dumps(event_dict)
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

