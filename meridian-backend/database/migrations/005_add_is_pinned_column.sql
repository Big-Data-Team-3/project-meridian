-- Migration: Add is_pinned column to conversations table
-- Description: Ensures is_pinned column exists in meridian.conversations table
-- This is a safety migration to handle cases where the table was created before is_pinned was added

-- Add is_pinned column if it doesn't exist
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
            RAISE NOTICE 'Added is_pinned column to meridian.conversations';
        ELSE
            RAISE NOTICE 'Column is_pinned already exists in meridian.conversations';
        END IF;
    ELSE
        RAISE NOTICE 'Table meridian.conversations does not exist';
    END IF;
END $$;

