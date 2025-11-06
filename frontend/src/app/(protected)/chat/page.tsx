"use client";

import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { MessageList } from "@/components/chat/MessageList";
import { ChatInput } from "@/components/chat/ChatInput";
import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface AgentState extends Record<string, unknown> {
  messages: Message[];
  ui?: Array<{
    id: string;
    name: string;
    props: Record<string, unknown>;
    metadata?: {
      message_id?: string;
    };
  }>;
}

export default function ChatPage() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [userId, setUserId] = useState<string | null>(null);

  // Get user ID from Supabase auth
  // Note: user_id will be injected into config by API route
  useEffect(() => {
    const supabase = createClient();
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserId(user.id);
      }
    };
    getUser();
  }, []);

  // Construct absolute URL for API route (synchronously for useStream)
  const apiUrl = typeof window !== "undefined" 
    ? `${window.location.origin}/api`
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:2024";

  const thread = useStream<AgentState>({
    apiUrl: apiUrl, // Use Next.js API route to inject user_id
    assistantId: "agent",
    messagesKey: "messages",
  });

  // Auto-scroll to bottom when new messages arrive or when loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread.messages, thread.isLoading]);

  const handleSubmit = (message: string) => {
    // user_id is automatically injected by API route from session
    thread.submit({
      messages: [{ type: "human", content: message }],
    });
  };

  const handleStop = () => {
    thread.stop();
  };

  return (
    <div className="flex flex-col h-screen w-full">
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          {thread.messages.length === 0 && !thread.isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4 max-w-md">
                <h1 className="text-2xl font-bold">Start a conversation</h1>
                <p className="text-muted-foreground">
                  Ask me anything about job searching, company research, or resume tailoring.
                </p>
              </div>
            </div>
          ) : (
            <MessageList 
              messages={thread.messages} 
              isLoading={thread.isLoading}
              uiMessages={thread.values?.ui as AgentState["ui"]}
              thread={thread}
            />
          )}
          <div ref={messagesEndRef} />
        </div>
        <ChatInput
          onSubmit={handleSubmit}
          onStop={handleStop}
          isLoading={thread.isLoading}
          disabled={!!thread.error}
        />
        {thread.error ? (
          <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
            {`Error: ${
              thread.error instanceof Error
                ? thread.error.message
                : String(thread.error)
            }`}
          </div>
        ) : null}
      </div>
    </div>
  );
}
