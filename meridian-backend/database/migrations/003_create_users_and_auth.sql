-- Migration: Create users and auth_credentials tables
-- Description: Creates tables for user authentication and management

-- Create meridian schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS meridian;

-- Create users table
CREATE TABLE IF NOT EXISTS meridian.users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    gcp_user_id VARCHAR(255),
    gcp_email VARCHAR(255),
    gcp_provider VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at TIMESTAMP
);

-- Create indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON meridian.users(email);
CREATE INDEX IF NOT EXISTS idx_users_gcp_user_id ON meridian.users(gcp_user_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON meridian.users(is_active);

-- Create auth_credentials table
CREATE TABLE IF NOT EXISTS meridian.auth_credentials (
    credential_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    id_token TEXT,
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'google',
    provider_user_id VARCHAR(255),
    provider_email VARCHAR(255),
    expires_at TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    FOREIGN KEY (user_id) REFERENCES meridian.users(user_id) ON DELETE CASCADE
);

-- Create indexes for auth_credentials table
CREATE INDEX IF NOT EXISTS idx_auth_credentials_user_id ON meridian.auth_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_credentials_active ON meridian.auth_credentials(is_active);
CREATE INDEX IF NOT EXISTS idx_auth_credentials_expires ON meridian.auth_credentials(expires_at);

