"use client";

import { useState, FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Send, Square } from "lucide-react";
import { ChatInput as ChatInputComponent } from "@/components/ui/chat-input";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  onStop?: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function ChatInput({
  onSubmit,
  onStop,
  isLoading = false,
  disabled = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (value.trim() && !disabled && !isLoading) {
      onSubmit(value);
      setValue("");
    }
  };

  return (
    <div className="border-t border-border bg-background">
      <form
        onSubmit={handleSubmit}
        className="relative rounded-lg border bg-background focus-within:ring-1 focus-within:ring-ring m-4"
      >
        <ChatInputComponent
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Type your message here..."
          className="min-h-[80px] resize-none rounded-lg bg-background border-0 p-3 shadow-none focus-visible:ring-0"
          disabled={disabled || isLoading}
        />
        <div className="flex items-center justify-end p-3 pt-2 gap-2">
          {isLoading ? (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={onStop}
              className="gap-1.5"
            >
              <Square className="size-3.5" />
              Stop
            </Button>
          ) : (
            <Button
              type="submit"
              size="sm"
              disabled={!value.trim() || disabled}
              className="gap-1.5"
            >
              Send
              <Send className="size-3.5" />
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

