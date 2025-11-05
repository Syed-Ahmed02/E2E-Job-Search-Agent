"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface ToolCallProps {
  toolCall: {
    id?: string;
    name: string;
    args: Record<string, unknown>;
  };
}

export function ToolCall({ toolCall }: ToolCallProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded-lg bg-muted/50 border border-border overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">🔧 {toolCall.name}</span>
          <span className="text-xs text-muted-foreground">
            {Object.keys(toolCall.args).length} argument
            {Object.keys(toolCall.args).length !== 1 ? "s" : ""}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      {isExpanded && (
        <div className="p-3 pt-0 border-t border-border">
          <div className="text-xs font-medium text-muted-foreground mb-2">
            Arguments:
          </div>
          <pre className="text-xs font-mono bg-background p-2 rounded overflow-x-auto">
            {JSON.stringify(toolCall.args, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

