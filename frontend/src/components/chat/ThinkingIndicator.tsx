"use client";

import { Bot } from "lucide-react";

export function ThinkingIndicator() {
  return (
    <div className="flex gap-3 justify-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
        <Bot className="w-4 h-4 text-primary-foreground" />
      </div>
      <div className="flex flex-col gap-2 max-w-[80%] items-start">
        <div className="rounded-lg bg-muted p-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span>Thinking</span>
            <div className="flex gap-1">
              <span 
                className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" 
                style={{ animationDelay: "0ms" }}
              ></span>
              <span 
                className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" 
                style={{ animationDelay: "150ms" }}
              ></span>
              <span 
                className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" 
                style={{ animationDelay: "300ms" }}
              ></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

