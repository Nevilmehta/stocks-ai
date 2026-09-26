import ReactMarkdown from "react-markdown";

import { cn } from "@/lib/utils";

export function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("space-y-3 text-sm leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0", className)}>
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="leading-relaxed">{children}</p>,
          h1: ({ children }) => <h3 className="text-base font-semibold">{children}</h3>,
          h2: ({ children }) => <h3 className="text-base font-semibold">{children}</h3>,
          h3: ({ children }) => <h4 className="font-semibold">{children}</h4>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
              {children}
            </a>
          ),
          code: ({ children }) => <code className="rounded bg-black/10 px-1 py-0.5 text-xs dark:bg-white/10">{children}</code>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
