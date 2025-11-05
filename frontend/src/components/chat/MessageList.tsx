"use client";

import type { Message } from "@langchain/langgraph-sdk";
import { ToolCall } from "./ToolCall";
import { ToolOutput } from "./ToolOutput";
import { MarkdownContent } from "./MarkdownContent";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { User, Bot } from "lucide-react";

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

export function MessageList({ messages, isLoading = false }: MessageListProps) {
  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto">
      {messages.map((message) => {
        const isHuman = message.type === "human";
        const isAI = message.type === "ai";
        const isTool = message.type === "tool";

        return (
          <div
            key={message.id}
            className={`flex gap-3 ${
              isHuman ? "justify-end" : "justify-start"
            }`}
          >
            {!isHuman && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
            )}

            <div
              className={`flex flex-col gap-2 max-w-[80%] ${
                isHuman ? "items-end" : "items-start"
              }`}
            >
              {isAI && (
                <div className="rounded-lg bg-muted p-3 text-sm">
                  <MarkdownContent content={message.content} />
                </div>
              )}

              {isHuman && (
                <div className="rounded-lg bg-primary text-primary-foreground p-3 text-sm [&_.prose]:text-primary-foreground [&_.prose_a]:text-primary-foreground [&_.prose_strong]:text-primary-foreground">
                  <MarkdownContent content={message.content} />
                </div>
              )}

              {isTool && (
                <ToolOutput
                  toolName={message.name || "Unknown"}
                  content={message.content}
                />
              )}

              {/* Render tool calls for AI messages */}
              {isAI &&
                "tool_calls" in message &&
                message.tool_calls &&
                Array.isArray(message.tool_calls) &&
                message.tool_calls.length > 0 && (
                  <div className="flex flex-col gap-2 mt-2">
                    {message.tool_calls.map((toolCall, index) => (
                      <ToolCall
                        key={
                          (toolCall as { id?: string }).id ||
                          `${message.id}-tool-${index}`
                        }
                        toolCall={toolCall as { id?: string; name: string; args: Record<string, unknown> }}
                      />
                    ))}
                  </div>
                )}
            </div>

            {isHuman && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <User className="w-4 h-4 text-secondary-foreground" />
              </div>
            )}
          </div>
        );
      })}
      {isLoading && <ThinkingIndicator />}
    </div>
  );
}

