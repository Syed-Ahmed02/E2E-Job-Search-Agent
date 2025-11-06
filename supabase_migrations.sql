-- Migration: Create chat_history and user_jobs tables
-- Run this in your Supabase SQL editor

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_chat_history_user_thread ON chat_history(user_id, thread_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at DESC);

-- Create user_jobs table (no thread_id link)
CREATE TABLE IF NOT EXISTS user_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    match_rating INTEGER CHECK (match_rating >= 0 AND match_rating <= 5),
    link TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_jobs_user_id ON user_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_user_jobs_created_at ON user_jobs(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_jobs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_history
-- Allow users to view their own chat history
CREATE POLICY "Users can view their own chat history"
    ON chat_history FOR SELECT
    USING (auth.uid() = user_id);

-- Allow users to insert their own chat history
CREATE POLICY "Users can insert their own chat history"
    ON chat_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Allow service role (backend) to insert chat history for any user
-- This is needed for server-side operations
CREATE POLICY "Service role can insert chat history"
    ON chat_history FOR INSERT
    WITH CHECK (
        current_setting('request.jwt.claim.role', true) = 'service_role'
        OR auth.uid() = user_id
    );

-- Allow service role to view chat history (for debugging/admin purposes)
CREATE POLICY "Service role can view chat history"
    ON chat_history FOR SELECT
    USING (
        current_setting('request.jwt.claim.role', true) = 'service_role'
        OR auth.uid() = user_id
    );

-- RLS Policies for user_jobs
-- Allow users to view their own jobs
CREATE POLICY "Users can view their own jobs"
    ON user_jobs FOR SELECT
    USING (auth.uid() = user_id);

-- Allow users to insert their own jobs
CREATE POLICY "Users can insert their own jobs"
    ON user_jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Allow service role (backend) to insert jobs for any user
CREATE POLICY "Service role can insert jobs"
    ON user_jobs FOR INSERT
    WITH CHECK (
        current_setting('request.jwt.claim.role', true) = 'service_role'
        OR auth.uid() = user_id
    );

-- Allow service role to view jobs (for debugging/admin purposes)
CREATE POLICY "Service role can view jobs"
    ON user_jobs FOR SELECT
    USING (
        current_setting('request.jwt.claim.role', true) = 'service_role'
        OR auth.uid() = user_id
    );

