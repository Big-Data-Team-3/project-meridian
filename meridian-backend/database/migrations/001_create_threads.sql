-- Migration: Create threads table
-- Description: Creates the threads table for storing conversation threads

-- Create meridian schema if it doesn't exist (idempotent)
CREATE SCHEMA IF NOT EXISTS meridian;

-- Create threads table in meridian schema
CREATE TABLE IF NOT EXISTS meridian.threads (
    thread_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id VARCHAR(255)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON meridian.threads(created_at);
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON meridian.threads(user_id);

