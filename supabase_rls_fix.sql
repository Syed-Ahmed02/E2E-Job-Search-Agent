-- Fix RLS policies to allow service role operations
-- Run this in your Supabase SQL editor after the main migration
-- NOTE: Service role key should automatically bypass RLS, but this ensures it works

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Users can insert their own chat history" ON chat_history;
DROP POLICY IF EXISTS "Service role can insert chat history" ON chat_history;
DROP POLICY IF EXISTS "Allow insert chat history" ON chat_history;
DROP POLICY IF EXISTS "Users can insert their own jobs" ON user_jobs;
DROP POLICY IF EXISTS "Service role can insert jobs" ON user_jobs;
DROP POLICY IF EXISTS "Allow insert jobs" ON user_jobs;

-- Create INSERT policies that work for both authenticated users and service role
-- For service role: RLS is bypassed automatically, but we add explicit check as backup
-- For users: Must match their user_id
CREATE POLICY "Allow insert chat history"
    ON chat_history FOR INSERT
    WITH CHECK (
        -- Allow if using service role (backend operations)
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Allow if user matches their own user_id (client operations)
        auth.uid() = user_id
    );

CREATE POLICY "Allow insert jobs"
    ON user_jobs FOR INSERT
    WITH CHECK (
        -- Allow if using service role (backend operations)
        auth.jwt() ->> 'role' = 'service_role'
        OR
        -- Allow if user matches their own user_id (client operations)
        auth.uid() = user_id
    );

-- Note: SELECT policies remain user-specific for security

