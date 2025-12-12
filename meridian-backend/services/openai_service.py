"""
OpenAI service for chat completions.
Handles OpenAI API integration with error handling and rate limiting.
"""
import os
import logging
from typing import List, Dict, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  openai package not installed. Install with: pip install openai")

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        """Initialize OpenAI service."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Initialize OpenAI client
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        logger.info(f"OpenAI service initialized with model: {self.model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1000
    ) -> str:
        """
        Get chat completion from OpenAI.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            Assistant response content
        
        Raises:
            Exception: If API call fails
        """
        try:
            model = model or self.model
            
            logger.debug(f"Calling OpenAI API with {len(messages)} messages")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            logger.debug(f"OpenAI API response received ({len(content)} chars)")
            
            return content
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit error: {e}")
            raise Exception(f"OpenAI API rate limit exceeded: {str(e)}")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}", exc_info=True)
            raise Exception(f"Failed to get OpenAI response: {str(e)}")
    
    def format_messages_for_openai(
        self, 
        conversation_history: List[Dict], 
        include_system_prompt: bool = True
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for OpenAI API.
        
        Args:
            conversation_history: List of message dicts with 'role' and 'content'
            include_system_prompt: Whether to include Meridian system prompt
        
        Returns:
            Formatted messages for OpenAI API
        """
        messages = []
        
        # Add system prompt if requested
        if include_system_prompt:
            system_prompt = """You are Meridian, an intelligent financial analysis assistant powered by a multi-agent AI system. You help users with:

- General questions and conversation
- Financial market education and concepts
- Investment strategy discussions
- Company and stock information
- Market analysis and insights

While you can handle casual conversation, your primary expertise is in financial markets, investing, and economic analysis. When users ask financial questions, provide thoughtful, well-informed responses. For complex financial analysis requiring real-time data, you can leverage specialized agent workflows.

Be friendly, professional, and helpful. Always maintain the context that you are Meridian, a financial intelligence platform."""
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        messages.extend([
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            }
            for msg in conversation_history
        ])
        
        return messages


# Global service instance
_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    """
    Get or create global OpenAI service instance.
    
    Returns:
        OpenAIService instance
    """
    global _service
    if _service is None:
        _service = OpenAIService()
    return _service

