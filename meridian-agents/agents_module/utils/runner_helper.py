"""
Helper utility to run Runner.run_sync() in an isolated thread without event loop conflicts.
"""
import concurrent.futures
import threading
import asyncio
from typing import Any, Callable


def run_agent_sync(agent, user_message, timeout: int = 300) -> Any:
    """
    Run Runner.run_sync() in an isolated thread to avoid event loop conflicts.
    
    Args:
        agent: The agent to run
        user_message: The user message to send
        timeout: Timeout in seconds (default: 300)
    
    Returns:
        The result from Runner.run_sync()
    """
    from agents import Runner
    
    def _run_in_isolated_thread():
        """Run in a thread with no event loop context."""
        # Ensure this thread has no event loop
        # Set event loop to None for this thread
        try:
            # Get current event loop (if any)
            try:
                loop = asyncio.get_event_loop()
                # If we get here and loop is running, we have a problem
                if hasattr(loop, 'is_running') and loop.is_running():
                    # Force close and set to None
                    try:
                        loop.close()
                    except:
                        pass
            except RuntimeError:
                # No event loop exists - this is good
                pass
            
            # Explicitly set event loop to None for this thread
            asyncio.set_event_loop(None)
        except Exception:
            # If anything fails, continue anyway
            pass
        
        # Now run the sync method - this should work in a thread with no event loop
        return Runner.run_sync(agent, user_message)
    
    # Use ThreadPoolExecutor to run in a completely isolated thread
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_in_isolated_thread)
        try:
            result = future.result(timeout=timeout)
            return result
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Agent execution timed out after {timeout} seconds")
        except Exception as e:
            raise e

