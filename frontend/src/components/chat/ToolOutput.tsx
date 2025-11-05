"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ToolOutputProps {
  toolName: string;
  content: string | unknown;
}

export function ToolOutput({ toolName, content }: ToolOutputProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const contentString =
    typeof content === "string" ? content : JSON.stringify(content, null, 2);

  return (
    <div className="rounded-lg bg-muted/50 border border-border overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">🔧 {toolName}</span>
          <span className="text-xs text-muted-foreground">Tool Output</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-border">
          <div className="prose prose-sm dark:prose-invert max-w-none break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="my-2 ml-4 list-disc">{children}</ul>,
                ol: ({ children }) => <ol className="my-2 ml-4 list-decimal">{children}</ol>,
                li: ({ children }) => <li className="mb-1">{children}</li>,
                h1: ({ children }) => <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0">{children}</h1>,
                h2: ({ children }) => <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
                h3: ({ children }) => <h3 className="text-base font-bold mb-1 mt-2 first:mt-0">{children}</h3>,
                code: ({ children, className }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code className="bg-background px-1 py-0.5 rounded text-xs font-mono">{children}</code>
                  ) : (
                    <code className={className}>{children}</code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="bg-background p-2 rounded overflow-x-auto my-2">{children}</pre>
                ),
                a: ({ children, href }) => (
                  <a href={href} className="text-primary underline hover:text-primary/80" target="_blank" rel="noopener noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {contentString}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

