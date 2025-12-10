"""
Message service for managing conversation messages.
Handles all message-related database operations using meridian schema.
"""
import uuid
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import text

from database.cloud_sql_client import get_db_client

logger = logging.getLogger(__name__)


class MessageService:
    """Service for message management operations."""
    
    def __init__(self):
        """Initialize message service."""
        self.db_client = get_db_client()
    
    def _get_next_sequence_number(self, conversation_id: str) -> int:
        """
        Get next sequence number for a conversation's messages.
        
        Args:
            conversation_id: Conversation UUID as string
        
        Returns:
            Next sequence number
        """
        query = text("""
            SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_sequence
            FROM meridian.messages
            WHERE conversation_id = :conversation_id
        """)
        
        with self.db_client.get_connection() as conn:
            result = conn.execute(query, {"conversation_id": conversation_id})
            row = result.fetchone()
            return row[0] if row else 1
    
    async def save_user_message(
        self,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Save a user message to the database.
        
        Args:
            thread_id: Conversation identifier (UUID string, maps to conversation_id)
            content: Message content
            metadata: Optional message metadata
        
        Returns:
            Dictionary with saved message data
        """
        message_id = uuid.uuid4()
        sequence_number = self._get_next_sequence_number(thread_id)
        
        query = text("""
            INSERT INTO meridian.messages 
                (message_id, conversation_id, role, content, sequence_number, metadata, created_at, updated_at)
            VALUES 
                (:message_id, :conversation_id, :role, :content, :sequence_number, :metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING message_id, conversation_id, role, content, sequence_number, metadata, created_at, updated_at
        """)
        
        def _save_message():
            import json
            with self.db_client.get_connection() as conn:
                # For JSONB, we can pass dict directly - SQLAlchemy/psycopg2 handles it
                # But to be safe with raw SQL, convert to JSON string
                metadata_param = json.dumps(metadata) if metadata else None
                
                result = conn.execute(
                    query,
                    {
                        "message_id": str(message_id),
                        "conversation_id": thread_id,
                        "role": "user",
                        "content": content,
                        "sequence_number": sequence_number,
                        "metadata": metadata_param
                    }
                )
                conn.commit()
                row = result.fetchone()
                # JSONB returns as dict in psycopg2, but handle both cases
                metadata_result = row[5]
                if isinstance(metadata_result, str):
                    try:
                        metadata_result = json.loads(metadata_result)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                return {
                    "message_id": str(row[0]),
                    "thread_id": str(row[1]),  # Map conversation_id to thread_id for API
                    "role": row[2],
                    "content": row[3],
                    "sequence_number": row[4],
                    "timestamp": row[6].isoformat() if row[6] else None,  # Use created_at as timestamp
                    "metadata": metadata_result
                }
        
        try:
            result = await asyncio.to_thread(_save_message)
            logger.info(f"User message saved: {message_id} in conversation {thread_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to save user message: {e}", exc_info=True)
            raise Exception(f"Failed to save user message: {str(e)}")
    
    async def save_assistant_message(
        self,
        thread_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Save an assistant message to the database.
        
        Args:
            thread_id: Conversation identifier (UUID string, maps to conversation_id)
            content: Message content
            metadata: Optional message metadata
        
        Returns:
            Dictionary with saved message data
        """
        message_id = uuid.uuid4()
        sequence_number = self._get_next_sequence_number(thread_id)
        
        query = text("""
            INSERT INTO meridian.messages 
                (message_id, conversation_id, role, content, sequence_number, metadata, created_at, updated_at)
            VALUES 
                (:message_id, :conversation_id, :role, :content, :sequence_number, :metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING message_id, conversation_id, role, content, sequence_number, metadata, created_at, updated_at
        """)
        
        def _save_message():
            import json
            with self.db_client.get_connection() as conn:
                # For JSONB, we can pass dict directly - SQLAlchemy/psycopg2 handles it
                # But to be safe with raw SQL, convert to JSON string
                metadata_param = json.dumps(metadata) if metadata else None
                
                result = conn.execute(
                    query,
                    {
                        "message_id": str(message_id),
                        "conversation_id": thread_id,
                        "role": "assistant",
                        "content": content,
                        "sequence_number": sequence_number,
                        "metadata": metadata_param
                    }
                )
                conn.commit()
                row = result.fetchone()
                # JSONB returns as dict in psycopg2, but handle both cases
                metadata_result = row[5]
                if isinstance(metadata_result, str):
                    try:
                        metadata_result = json.loads(metadata_result)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                return {
                    "message_id": str(row[0]),
                    "thread_id": str(row[1]),  # Map conversation_id to thread_id for API
                    "role": row[2],
                    "content": row[3],
                    "sequence_number": row[4],
                    "timestamp": row[6].isoformat() if row[6] else None,  # Use created_at as timestamp
                    "metadata": metadata_result
                }
        
        try:
            result = await asyncio.to_thread(_save_message)
            logger.info(f"Assistant message saved: {message_id} in conversation {thread_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}", exc_info=True)
            raise Exception(f"Failed to save assistant message: {str(e)}")
    
    async def get_messages_by_thread(
        self,
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        Get all messages for a conversation, ordered by sequence number.
        
        Args:
            thread_id: Conversation identifier (UUID string)
            limit: Optional limit on number of messages
        
        Returns:
            List of message dictionaries ordered by sequence (ascending)
        """
        if limit:
            query = text("""
                SELECT message_id, conversation_id, role, content, sequence_number, metadata, created_at
                FROM meridian.messages
                WHERE conversation_id = :conversation_id
                ORDER BY sequence_number ASC
                LIMIT :limit
            """)
            params = {"conversation_id": thread_id, "limit": limit}
        else:
            query = text("""
                SELECT message_id, conversation_id, role, content, sequence_number, metadata, created_at
                FROM meridian.messages
                WHERE conversation_id = :conversation_id
                ORDER BY sequence_number ASC
            """)
            params = {"conversation_id": thread_id}
        
        def _get_messages():
            with self.db_client.get_connection() as conn:
                result = conn.execute(query, params)
                messages = []
                for row in result:
                    messages.append({
                        "message_id": str(row[0]),
                        "thread_id": str(row[1]),  # Map conversation_id to thread_id for API
                        "role": row[2],
                        "content": row[3],
                        "sequence_number": row[4],
                        "timestamp": row[6].isoformat() if row[6] else None,  # Use created_at as timestamp
                        "metadata": row[5]
                    })
                return messages
        
        try:
            messages = await asyncio.to_thread(_get_messages)
            logger.info(f"Retrieved {len(messages)} messages for conversation {thread_id}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {thread_id}: {e}", exc_info=True)
            raise Exception(f"Failed to get messages: {str(e)}")
    
    async def get_conversation_context(
        self,
        thread_id: str,
        max_messages: int = 20
    ) -> List[Dict[str, str]]:
        """
        Get conversation context (last N messages) formatted for OpenAI API.
        Uses sequence_number for ordering (most recent = highest sequence).
        
        Args:
            thread_id: Conversation identifier (UUID string)
            max_messages: Maximum number of messages to include
        
        Returns:
            List of message dicts with 'role' and 'content' for OpenAI API
        """
        query = text("""
            SELECT role, content, sequence_number
            FROM meridian.messages
            WHERE conversation_id = :conversation_id
            ORDER BY sequence_number DESC
            LIMIT :max_messages
        """)
        
        def _get_context():
            with self.db_client.get_connection() as conn:
                result = conn.execute(
                    query,
                    {
                        "conversation_id": thread_id,
                        "max_messages": max_messages
                    }
                )
                # Reverse to get chronological order (oldest first, lowest sequence first)
                messages = []
                rows = list(result)
                for row in reversed(rows):
                    messages.append({
                        "role": row[0],
                        "content": row[1]
                    })
                return messages
        
        try:
            messages = await asyncio.to_thread(_get_context)
            logger.debug(f"Retrieved {len(messages)} messages for context (conversation {thread_id})")
            return messages
        except Exception as e:
            logger.error(f"Failed to get conversation context for conversation {thread_id}: {e}", exc_info=True)
            raise Exception(f"Failed to get conversation context: {str(e)}")
