-- Migration: Create threads table
-- Description: Creates the threads table for storing conversation threads

CREATE TABLE IF NOT EXISTS threads (
    thread_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id VARCHAR(255)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);

