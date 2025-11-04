"use client";

import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { useState, useRef, useEffect } from "react";
import { ChatInput } from "@/components/ui/chat-input";
import { Button } from "@/components/ui/button";
import { CornerDownLeft, StopCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type State = {
  messages: Message[];
};

function isError(error: unknown): error is Error {
  return error instanceof Error;
}

function getErrorMessage(error: unknown): string {
  if (isError(error)) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return "An unknown error occurred";
}

function renderMessageContent(
  content: string | unknown[] | unknown
): React.ReactNode {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    return content.map((item, idx) => {
      if (typeof item === "string") {
        return <span key={idx}>{item}</span>;
      }
      if (
        typeof item === "object" &&
        item !== null &&
        "type" in item &&
        "text" in item &&
        item.type === "text"
      ) {
        return <span key={idx}>{String(item.text)}</span>;
      }
      return <span key={idx}>{JSON.stringify(item)}</span>;
    });
  }
  if (typeof content === "object" && content !== null) {
    return JSON.stringify(content, null, 2);
  }
  return String(content);
}

export function ChatClient() {
  const [input, setInput] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Get API URL from environment variable or default to localhost
  const apiUrl: string =
    process.env.NEXT_PUBLIC_LANGGRAPH_API_URL || "http://localhost:2024";
  
  const thread = useStream<State>({
    apiUrl,
    assistantId: "agent",
    messagesKey: "messages",
    reconnectOnMount: true,
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread.messages]);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!input.trim() || thread.isLoading) return;

    const message = input.trim();
    setInput("");

    thread.submit(
      { messages: [{ type: "human" as const, content: message }] },
      {
        optimisticValues(prev: State): State {
          const prevMessages = prev.messages ?? [];
          const newMessage: Message = {
            id: `optimistic-${Date.now()}`,
            type: "human",
            content: message,
          };
          return { ...prev, messages: [...prevMessages, newMessage] };
        },
      }
    );
  };

  return (
    <div className="flex flex-col h-full w-full max-w-4xl mx-auto">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {thread.messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center space-y-2">
              <h3 className="text-lg font-semibold">Start a conversation</h3>
              <p className="text-sm">
                Ask me about job search, company research, or resume tailoring.
              </p>
            </div>
          </div>
        )}

        {thread.messages.map((message) => {
          const isHuman = message.type === "human";
          return (
            <div
              key={message.id}
              className={cn(
                "flex w-full",
                isHuman ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "rounded-lg px-4 py-2 max-w-[80%]",
                  isHuman
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground"
                )}
              >
                <div className="text-sm whitespace-pre-wrap break-words">
                  {renderMessageContent(message.content)}
                </div>
              </div>
            </div>
          );
        })}

        {thread.isLoading && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-2 bg-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          </div>
        )}

        {thread.error !== null && thread.error !== undefined && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-2 bg-destructive/10 text-destructive">
              <p className="text-sm">Error: {getErrorMessage(thread.error)}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="space-y-2">
          <div className="relative rounded-lg border bg-background focus-within:ring-1 focus-within:ring-ring">
            <ChatInput
              value={input}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                setInput(e.target.value)
              }
              placeholder="Type your message here..."
              className="min-h-[60px] resize-none rounded-lg bg-background border-0 p-3 shadow-none focus-visible:ring-0"
              disabled={thread.isLoading}
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  const form = e.currentTarget.closest("form");
                  if (form instanceof HTMLFormElement) {
                    form.requestSubmit();
                  }
                }
              }}
            />
            <div className="flex items-center p-2">
              <div className="flex-1" />
              {thread.isLoading ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={(): void => {
                    void thread.stop();
                  }}
                  className="gap-1.5"
                >
                  <StopCircle className="h-4 w-4" />
                  Stop
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="sm"
                  disabled={!input.trim()}
                  className="gap-1.5"
                >
                  Send
                  <CornerDownLeft className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

