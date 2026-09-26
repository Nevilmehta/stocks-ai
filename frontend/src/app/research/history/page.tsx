"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquareText } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { api } from "@/lib/api";
import type { ResearchSessionSummary } from "@/types";

export default function ResearchHistoryPage() {
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<ResearchSessionSummary[]>("/api/research/history")
      .then(setSessions)
      .catch(() => toast.error("Failed to load research history."))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-3xl space-y-6 px-4 py-10 sm:px-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Research history</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Every AI Analyse and chat exchange you&apos;ve run, saved so you can reopen it later.
            </p>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <MessageSquareText className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No research yet. Head to the{" "}
                  <Link href="/research" className="underline underline-offset-2">
                    research chat
                  </Link>{" "}
                  or click &quot;AI Analyse&quot; on any stock page.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <Link key={session.id} href={`/research?session=${session.id}`}>
                  <Card className="transition-colors hover:border-primary/40">
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-medium">{session.title}</p>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {new Date(session.created_at).toLocaleString()}
                        </span>
                      </div>
                      {session.last_message_preview && (
                        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                          {session.last_message_preview}
                        </p>
                      )}
                      <p className="mt-2 text-xs text-muted-foreground">{session.message_count} messages</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
