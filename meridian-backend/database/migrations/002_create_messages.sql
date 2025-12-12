-- Migration: Create messages table
-- Description: Creates the messages table for storing conversation messages

-- Create meridian schema if it doesn't exist (idempotent)
CREATE SCHEMA IF NOT EXISTS meridian;

-- Create messages table in meridian schema
CREATE TABLE IF NOT EXISTS meridian.messages (
    message_id VARCHAR(255) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),  -- Keep for backward compatibility (maps to conversation_id)
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sequence_number INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create composite index for efficient message retrieval by conversation and sequence
CREATE INDEX IF NOT EXISTS idx_messages_conversation_sequence ON meridian.messages(conversation_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_messages_thread_timestamp ON meridian.messages(thread_id, timestamp) WHERE thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON meridian.messages(conversation_id);

-- Add foreign key to conversations table (will be added after conversations table is created in migration 004)
-- This is handled in migration 004 to avoid dependency issues

