"""
SQLAlchemy models for database tables.
Defines Thread and Message models for Cloud SQL.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Thread(Base):
    """Thread model for storing conversation threads."""
    __tablename__ = "threads"
    
    thread_id = Column(String(255), primary_key=True, nullable=False)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    user_id = Column(String(255), nullable=True)  # For future multi-user support
    
    # Indexes
    __table_args__ = (
        Index('idx_threads_created_at', 'created_at'),
        Index('idx_threads_user_id', 'user_id'),
    )
    
    def to_dict(self):
        """Convert thread to dictionary."""
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id
        }


class Message(Base):
    """Message model for storing conversation messages."""
    __tablename__ = "messages"
    
    message_id = Column(String(255), primary_key=True, nullable=False)
    thread_id = Column(String(255), ForeignKey('threads.thread_id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    metadata = Column(JSON, nullable=True)  # For future extensions
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_messages_thread_timestamp', 'thread_id', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }

