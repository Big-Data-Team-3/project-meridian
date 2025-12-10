-- Migration: Create messages table
-- Description: Creates the messages table for storing conversation messages with foreign key to threads

CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(255) PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata JSON,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);

-- Create composite index for efficient message retrieval by thread and timestamp
CREATE INDEX IF NOT EXISTS idx_messages_thread_timestamp ON messages(thread_id, timestamp);

