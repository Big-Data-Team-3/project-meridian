-- Migration: Create conversations table
-- Description: Creates the conversations table for storing user conversation threads

-- Create meridian schema if it doesn't exist (idempotent)
CREATE SCHEMA IF NOT EXISTS meridian;

-- Create conversations table
CREATE TABLE IF NOT EXISTS meridian.conversations (
    conversation_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    sequence_number INTEGER NOT NULL DEFAULT 1,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON meridian.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_archived ON meridian.conversations(user_id, is_archived);
CREATE INDEX IF NOT EXISTS idx_conversations_sequence ON meridian.conversations(user_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON meridian.conversations(created_at);

-- Add foreign key to users table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meridian' AND table_name = 'users') THEN
        ALTER TABLE meridian.conversations
        ADD CONSTRAINT fk_conversations_user_id 
        FOREIGN KEY (user_id) REFERENCES meridian.users(user_id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add is_pinned column if it doesn't exist (for existing tables)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meridian' AND table_name = 'conversations') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'meridian' 
            AND table_name = 'conversations' 
            AND column_name = 'is_pinned'
        ) THEN
            ALTER TABLE meridian.conversations
            ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT FALSE;
        END IF;
    END IF;
END $$;

-- Add foreign key from messages to conversations table (if messages table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'meridian' AND table_name = 'messages') THEN
        -- Check if constraint already exists
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_schema = 'meridian' 
            AND table_name = 'messages' 
            AND constraint_name = 'fk_messages_conversation_id'
        ) THEN
            ALTER TABLE meridian.messages
            ADD CONSTRAINT fk_messages_conversation_id 
            FOREIGN KEY (conversation_id) REFERENCES meridian.conversations(conversation_id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

