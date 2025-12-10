"""
Thread service for managing conversation threads.
Handles all thread-related database operations using meridian schema.
"""
import uuid
import logging
import asyncio
from typing import Optional, List
from datetime import datetime

from sqlalchemy import text

from database.cloud_sql_client import get_db_client

logger = logging.getLogger(__name__)


class ThreadService:
    """Service for thread management operations."""
    
    def __init__(self):
        """Initialize thread service."""
        self.db_client = get_db_client()
    
    def _get_or_create_default_user(self) -> str:
        """
        Get or create a default user for testing.
        
        Returns:
            User UUID as string
        
        Raises:
            Exception: If database operation fails
        """
        try:
            query = text("""
                SELECT user_id FROM meridian.users 
                WHERE email = 'default@meridian.com'
                LIMIT 1
            """)
            
            with self.db_client.get_connection() as conn:
                result = conn.execute(query)
                row = result.fetchone()
                if row:
                    return str(row[0])
                
                # Create default user
                default_user_id = uuid.uuid4()
                create_user_query = text("""
                    INSERT INTO meridian.users (user_id, email, name, is_verified, is_active)
                    VALUES (:user_id, :email, :name, :is_verified, :is_active)
                    RETURNING user_id
                """)
                result = conn.execute(create_user_query, {
                    "user_id": str(default_user_id),
                    "email": "default@meridian.com",
                    "name": "Default User",
                    "is_verified": True,
                    "is_active": True
                })
                conn.commit()
                return str(default_user_id)
        except Exception as e:
            logger.error(f"Failed to get or create default user: {e}", exc_info=True)
            raise Exception(f"Database error: Failed to get or create default user: {str(e)}")
    
    def _get_next_sequence_number(self, user_id: str) -> int:
        """
        Get next sequence number for a user's conversation.
        
        Args:
            user_id: User UUID as string
        
        Returns:
            Next sequence number
        """
        query = text("""
            SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_sequence
            FROM meridian.conversations
            WHERE user_id = :user_id
        """)
        
        with self.db_client.get_connection() as conn:
            result = conn.execute(query, {"user_id": user_id})
            row = result.fetchone()
            return row[0] if row else 1
    
    async def create_thread(self, title: Optional[str] = None, user_id: Optional[str] = None) -> dict:
        """
        Create a new conversation (thread) in meridian schema.
        
        Args:
            title: Optional conversation title
            user_id: Optional user ID (UUID). If not provided, uses a default user.
        
        Returns:
            Dictionary with thread data (using thread_id for API compatibility)
        """
        # Use default user if not provided (for testing)
        # In production, user_id should always be provided
        if not user_id:
            user_id = self._get_or_create_default_user()
        
        # Get next sequence number
        sequence_number = self._get_next_sequence_number(user_id)
        
        # Generate conversation UUID
        conversation_id = uuid.uuid4()
        
        query = text("""
            INSERT INTO meridian.conversations 
                (conversation_id, user_id, title, sequence_number, created_at, updated_at)
            VALUES 
                (:conversation_id, :user_id, :title, :sequence_number, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING conversation_id, user_id, title, sequence_number, created_at, updated_at, message_count, last_message_at
        """)
        
        def _create_thread():
            with self.db_client.get_connection() as conn:
                result = conn.execute(
                    query,
                    {
                        "conversation_id": str(conversation_id),
                        "user_id": user_id,
                        "title": title,
                        "sequence_number": sequence_number
                    }
                )
                conn.commit()
                row = result.fetchone()
                return {
                    "thread_id": str(row[0]),  # Map conversation_id to thread_id for API
                    "conversation_id": str(row[0]),
                    "title": row[2],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "user_id": str(row[1]) if row[1] else None,
                    "sequence_number": row[3],
                    "message_count": row[6] if row[6] else 0
                }
        
        try:
            result = await asyncio.to_thread(_create_thread)
            logger.info(f"Conversation created: {conversation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}", exc_info=True)
            raise Exception(f"Failed to create conversation: {str(e)}")
    
    async def get_thread(self, thread_id: str) -> Optional[dict]:
        """
        Get a conversation by ID (thread_id maps to conversation_id).
        
        Args:
            thread_id: Conversation identifier (UUID string)
        
        Returns:
            Conversation data or None if not found
        """
        query = text("""
            SELECT conversation_id, user_id, title, sequence_number, created_at, updated_at, 
                   message_count, last_message_at, is_archived, is_pinned
            FROM meridian.conversations
            WHERE conversation_id = :conversation_id
        """)
        
        def _get_thread():
            with self.db_client.get_connection() as conn:
                result = conn.execute(query, {"conversation_id": thread_id})
                row = result.fetchone()
                if not row:
                    return None
                return {
                    "thread_id": str(row[0]),  # Map to thread_id for API
                    "conversation_id": str(row[0]),
                    "user_id": str(row[1]) if row[1] else None,
                    "title": row[2],
                    "sequence_number": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "message_count": row[6] if row[6] else 0,
                    "last_message_at": row[7].isoformat() if row[7] else None
                }
        
        try:
            return await asyncio.to_thread(_get_thread)
        except Exception as e:
            logger.error(f"Failed to get conversation {thread_id}: {e}", exc_info=True)
            raise Exception(f"Failed to get conversation: {str(e)}")
    
    async def list_threads(self, user_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """
        List all conversations, ordered by sequence (most recent first).
        
        Args:
            user_id: Optional user ID filter (UUID string)
            limit: Maximum number of conversations to return
        
        Returns:
            List of conversation dictionaries
        """
        if user_id:
            query = text("""
                SELECT conversation_id, user_id, title, sequence_number, created_at, updated_at,
                       message_count, last_message_at
                FROM meridian.conversations
                WHERE user_id = :user_id
                  AND is_archived = FALSE
                ORDER BY sequence_number ASC
                LIMIT :limit
            """)
            params = {"user_id": user_id, "limit": limit}
        else:
            query = text("""
                SELECT conversation_id, user_id, title, sequence_number, created_at, updated_at,
                       message_count, last_message_at
                FROM meridian.conversations
                WHERE is_archived = FALSE
                ORDER BY updated_at DESC, sequence_number ASC
                LIMIT :limit
            """)
            params = {"limit": limit}
        
        def _list_threads():
            with self.db_client.get_connection() as conn:
                result = conn.execute(query, params)
                threads = []
                for row in result:
                    threads.append({
                        "thread_id": str(row[0]),  # Map to thread_id for API
                        "conversation_id": str(row[0]),
                        "user_id": str(row[1]) if row[1] else None,
                        "title": row[2],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "updated_at": row[5].isoformat() if row[5] else None,
                        "message_count": row[6] if row[6] else 0
                    })
                return threads
        
        try:
            threads = await asyncio.to_thread(_list_threads)
            logger.info(f"Listed {len(threads)} conversations")
            return threads
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}", exc_info=True)
            raise Exception(f"Failed to list conversations: {str(e)}")
    
    async def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a conversation and all its messages (cascade delete).
        
        Args:
            thread_id: Conversation identifier (UUID string)
        
        Returns:
            True if deleted, False if not found
        """
        # First check if conversation exists
        conversation = await self.get_thread(thread_id)
        if not conversation:
            return False
        
        query = text("DELETE FROM meridian.conversations WHERE conversation_id = :conversation_id")
        
        def _delete_thread():
            with self.db_client.get_connection() as conn:
                # Cascade delete will automatically delete messages
                conn.execute(query, {"conversation_id": thread_id})
                conn.commit()
                return True
        
        try:
            await asyncio.to_thread(_delete_thread)
            logger.info(f"Conversation deleted: {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {thread_id}: {e}", exc_info=True)
            raise Exception(f"Failed to delete conversation: {str(e)}")
    
    async def update_thread_timestamp(self, thread_id: str):
        """
        Update conversation's updated_at timestamp.
        
        Args:
            thread_id: Conversation identifier (UUID string)
        """
        query = text("""
            UPDATE meridian.conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = :conversation_id
        """)
        
        def _update_timestamp():
            with self.db_client.get_connection() as conn:
                conn.execute(query, {"conversation_id": thread_id})
                conn.commit()
        
        try:
            await asyncio.to_thread(_update_timestamp)
        except Exception as e:
            logger.error(f"Failed to update conversation timestamp {thread_id}: {e}", exc_info=True)
            # Don't raise - this is a non-critical operation
