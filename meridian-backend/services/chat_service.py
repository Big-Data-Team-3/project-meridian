"""
Chat service for orchestrating chat interactions.
Handles message saving, OpenAI API calls, and response saving.
"""
import logging
from typing import Optional

from services.message_service import MessageService
from services.openai_service import get_openai_service
from services.thread_service import ThreadService
from utils.config import get_config

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations."""
    
    def __init__(self):
        """Initialize chat service."""
        self.message_service = MessageService()
        self.thread_service = ThreadService()
        self.openai_service = get_openai_service()
        self.config = get_config()
    
    async def process_chat_message(
        self,
        thread_id: str,
        user_message: str,
        user_id: str = None
    ) -> dict:
        """
        Process a chat message: save user message, get OpenAI response, save assistant response.
        Only processes messages for threads owned by the specified user.
        
        Args:
            thread_id: Thread identifier
            user_message: User message content
            user_id: Required user ID (UUID). Used to verify thread ownership.
        
        Returns:
            Dictionary with message IDs and assistant response
        
        Raises:
            ValueError: If user_id is not provided
            Exception: If thread not found or not owned by user, database error, or OpenAI API error
        """
        if not user_id:
            raise ValueError("user_id is required to process chat message")
        
        # Verify thread exists and belongs to user
        thread = await self.thread_service.get_thread(thread_id, user_id=user_id)
        if not thread:
            raise Exception(f"Thread {thread_id} not found")
        
        try:
            # 1. Save user message
            logger.info(f"Processing chat message for thread {thread_id}")
            user_msg = await self.message_service.save_user_message(
                thread_id=thread_id,
                content=user_message
            )
            
            # 2. Get conversation context (last N messages, already includes the newly saved user message)
            conversation_context = await self.message_service.get_conversation_context(
                thread_id=thread_id,
                max_messages=self.config.MAX_CONVERSATION_HISTORY
            )
            
            # 3. Format messages for OpenAI
            openai_messages = self.openai_service.format_messages_for_openai(conversation_context)
            
            # 4. Call OpenAI API
            logger.debug(f"Calling OpenAI API with {len(openai_messages)} messages")
            assistant_response = await self.openai_service.chat_completion(
                messages=openai_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # 5. Save assistant message
            assistant_msg = await self.message_service.save_assistant_message(
                thread_id=thread_id,
                content=assistant_response
            )
            
            # 6. Update thread timestamp
            await self.thread_service.update_thread_timestamp(thread_id)
            
            logger.info(
                f"Chat message processed: user_msg={user_msg['message_id']}, "
                f"assistant_msg={assistant_msg['message_id']}"
            )
            
            return {
                "thread_id": thread_id,
                "message_id": user_msg["message_id"],
                "assistant_message_id": assistant_msg["message_id"],
                "response": assistant_response
            }
            
        except Exception as e:
            logger.error(f"Failed to process chat message: {e}", exc_info=True)
            # Re-raise with context
            if "not found" in str(e).lower():
                raise Exception(f"Thread {thread_id} not found")
            elif "OpenAI" in str(e) or "openai" in str(e):
                raise Exception(f"OpenAI API error: {str(e)}")
            else:
                raise Exception(f"Failed to process chat message: {str(e)}")

