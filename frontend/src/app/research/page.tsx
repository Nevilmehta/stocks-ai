"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, Loader2, Menu, MessageSquarePlus, Send, Sparkles, User as UserIcon, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownContent } from "@/components/markdown-content";
import { Navbar } from "@/components/layout/navbar";
import { useAuth } from "@/context/auth-context";
import { ApiError, api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ResearchMessage, ResearchSession, ResearchSessionSummary } from "@/types";

const SUGGESTED_PROMPTS = [
  "Analyse Reliance Industries",
  "Compare TCS and Infosys",
  "Explain Tata Motors financial performance",
  "Is HDFC Bank valuation expensive compared with its fundamentals?",
];

function MessageBubble({ message }: { message: ResearchMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        {isUser ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%]",
          isUser ? "bg-primary text-primary-foreground whitespace-pre-wrap" : "bg-muted",
        )}
      >
        {isUser ? message.content : <MarkdownContent content={message.content} />}
      </div>
    </div>
  );
}

function ChatSidebar({
  sessions,
  isLoading,
  activeId,
  isOpen,
  onClose,
  onNewChat,
  onSelectSession,
}: {
  sessions: ResearchSessionSummary[];
  isLoading: boolean;
  activeId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
}) {
  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 top-16 z-30 bg-black/40 lg:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        className={cn(
          "fixed top-16 bottom-0 left-0 z-40 flex w-72 flex-col border-r bg-background transition-transform duration-200 ease-out lg:static lg:z-auto lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between gap-2 border-b p-3">
          <Button
            variant="outline"
            className="flex-1 justify-start gap-2"
            onClick={() => {
              onNewChat();
              onClose();
            }}
          >
            <MessageSquarePlus className="h-4 w-4" /> New chat
          </Button>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClose} aria-label="Close sidebar">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {isLoading ? (
            <div className="space-y-2 p-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <p className="p-3 text-xs text-muted-foreground">No chats yet. Start one below.</p>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => {
                    onSelectSession(session.id);
                    onClose();
                  }}
                  className={cn(
                    "block w-full truncate rounded-md px-3 py-2 text-left text-sm hover:bg-accent",
                    session.id === activeId && "bg-accent font-medium",
                  )}
                  title={session.title}
                >
                  {session.title}
                </button>
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

function ResearchChat() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ResearchMessage[]>([]);
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const autoSentRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const refreshSessions = () => {
    api
      .get<ResearchSessionSummary[]>("/api/research/history")
      .then(setSessions)
      .catch(() => {})
      .finally(() => setIsLoadingSessions(false));
  };

  useEffect(() => {
    refreshSessions();
  }, []);

  useEffect(() => {
    // Skip on initial mount (no messages yet) - scrolling an empty chat into
    // view pushes the page header off-screen for no reason.
    if (messages.length === 0) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text: string, currentSessionId: string | null) => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      { id: `pending-${Date.now()}`, role: "user", content: trimmed, created_at: new Date().toISOString() },
    ]);
    setInput("");

    try {
      const session = await api.post<ResearchSession>("/api/research/chat", {
        message: trimmed,
        session_id: currentSessionId ?? undefined,
      });
      setSessionId(session.id);
      setMessages(session.messages);
      if (searchParams.get("session") !== session.id) {
        router.replace(`/research?session=${session.id}`, { scroll: false });
      }
      refreshSessions();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to send message.");
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("pending-")));
    } finally {
      setIsSending(false);
    }
  };

  const loadSession = (id: string) => {
    if (id === sessionIdRef.current) return; // already showing this one
    let cancelled = false;
    setIsLoadingSession(true);
    api
      .get<ResearchSession>(`/api/research/history/${id}`)
      .then((session) => {
        if (cancelled) return;
        setSessionId(session.id);
        setMessages(session.messages);
        if (searchParams.get("session") !== session.id) {
          router.replace(`/research?session=${session.id}`, { scroll: false });
        }
      })
      .catch(() => {
        if (!cancelled) toast.error("Could not load that research session.");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingSession(false);
      });
    return () => {
      cancelled = true;
    };
  };

  useEffect(() => {
    const sessionParam = searchParams.get("session");
    const qParam = searchParams.get("q");

    if (sessionParam) {
      loadSession(sessionParam);
    } else if (qParam && !autoSentRef.current) {
      autoSentRef.current = true;
      sendMessage(qParam, null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setInput("");
    router.replace("/research", { scroll: false });
  };

  return (
    <div className="flex h-dvh flex-col">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <ChatSidebar
          sessions={sessions}
          isLoading={isLoadingSessions}
          activeId={sessionId}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          onNewChat={handleNewChat}
          onSelectSession={loadSession}
        />

        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="flex items-center gap-2 border-b p-3 lg:hidden">
            <Button variant="ghost" size="icon" onClick={() => setIsSidebarOpen(true)} aria-label="Open chat history">
              <Menu className="h-4 w-4" />
            </Button>
            <span className="text-sm font-medium">AI Research</span>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-end px-4 py-6 sm:px-6">
              {isLoadingSession ? (
                <div className="flex flex-1 items-center justify-center py-12 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Sparkles className="h-6 w-6" />
                  </span>
                  <div>
                    <h1 className="text-lg font-semibold">AI Research</h1>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {user ? `Hi ${user.display_name.split(" ")[0]}, ` : ""}ask about a company to get started.
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-center gap-2">
                    {SUGGESTED_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => sendMessage(prompt, null)}
                        className="rounded-full border px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}
                  {isSending && (
                    <div className="flex gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div className="flex items-center rounded-xl bg-muted px-4 py-3">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <div className="border-t p-4">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                sendMessage(input, sessionId);
              }}
              className="mx-auto flex w-full max-w-3xl items-center gap-2 rounded-full border bg-background py-1.5 pr-1.5 pl-5 shadow-sm"
            >
              <Input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask about a company..."
                disabled={isSending}
                className="h-9 flex-1 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
              />
              <Button
                type="submit"
                size="icon"
                className="h-9 w-9 shrink-0 rounded-full"
                disabled={isSending || !input.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </form>
            <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-muted-foreground">
              Answers are grounded in real computed metrics - never buy/sell advice.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <Suspense fallback={null}>
      <ResearchChat />
    </Suspense>
  );
}
