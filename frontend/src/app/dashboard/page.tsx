"use client";

import { useEffect, useMemo, useState, type ElementType } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, Clock, ListChecks, Megaphone, Search, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { AIScoreBadge } from "@/components/ai-score-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Pagination, PAGE_SIZE } from "@/components/pagination";
import { useAuth } from "@/context/auth-context";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatDate, formatPercent, formatPrice } from "@/lib/format";
import { brand } from "@/config/brand";
import type { AdminNote, Company, HealthStatus, MarketOverview, MoverStock, WatchlistItem } from "@/types";

const SUGGESTED_PROMPTS = [
  "Analyse Reliance Industries",
  "Compare TCS and Infosys",
  "Explain Tata Motors financial performance",
  "Is HDFC Bank valuation expensive compared with its fundamentals?",
];

function MoverList({
  title,
  icon: Icon,
  stocks,
  tone,
  onSelect,
}: {
  title: string;
  icon: ElementType;
  stocks: MoverStock[];
  tone: "up" | "down";
  onSelect: (symbol: string) => void;
}) {
  const toneClass = tone === "up" ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400";
  return (
    <Card>
      <CardHeader>
        <CardTitle className={cn("flex items-center gap-2 text-base", toneClass)}>
          <Icon className="h-4 w-4" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {stocks.length === 0 ? (
          <p className="text-sm text-muted-foreground">No {tone === "up" ? "gainers" : "losers"} today.</p>
        ) : (
          <div className="space-y-1">
            {stocks.map((stock) => (
              <button
                key={stock.symbol}
                onClick={() => onSelect(stock.symbol)}
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
              >
                <span>
                  <span className="font-medium">{stock.symbol}</span>{" "}
                  <span className="text-muted-foreground">{stock.name}</span>
                </span>
                <span className="flex items-center gap-3 tabular-nums">
                  <span className="text-muted-foreground">{formatPrice(stock.latest_price)}</span>
                  <span className={cn("w-16 text-right font-medium", toneClass)}>
                    {formatPercent(stock.change_percent)}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [adminNote, setAdminNote] = useState<AdminNote | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    Promise.all([
      api.get<Company[]>("/api/stocks"),
      api.get<HealthStatus>("/api/health"),
      api.get<MarketOverview>("/api/stocks/overview"),
      api.get<WatchlistItem[]>("/api/watchlist").catch(() => []),
      api.get<AdminNote | null>("/api/dashboard-note").catch(() => null),
    ])
      .then(([companyData, healthData, overviewData, watchlistData, noteData]) => {
        setCompanies(companyData);
        setHealth(healthData);
        setOverview(overviewData);
        setWatchlist(watchlistData);
        setAdminNote(noteData);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const filteredCompanies = useMemo(() => {
    const q = query.trim().toLowerCase();
    return companies.filter((company) => {
      const matchesQuery =
        !q ||
        company.symbol.toLowerCase().includes(q) ||
        company.name.toLowerCase().includes(q) ||
        company.sector.toLowerCase().includes(q);
      const matchesSector = !selectedSector || company.sector === selectedSector;
      return matchesQuery && matchesSector;
    });
  }, [companies, query, selectedSector]);

  // Reset to page 1 whenever the filtered set changes shape, so a search/
  // sector change doesn't leave the view stranded on a now-out-of-range page.
  useEffect(() => {
    setPage(1);
  }, [query, selectedSector]);

  const visibleCompanies = filteredCompanies.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const sectorCount = useMemo(() => new Set(companies.map((c) => c.sector)).size, [companies]);
  const isDemoData = health?.market_data_provider === "mock";
  // last_market_sync is the latest date we actually have priced data for -
  // correctly doesn't advance on an NSE holiday. last_sync_check_at is the
  // last time the system actually attempted a check at all (success or not,
  // new data or not), so a holiday still reads as "checked today" instead of
  // looking stale just because prices didn't change.
  const checkedDate = health?.last_sync_check_at?.slice(0, 10) ?? null;
  const dataIsBehindLastCheck = Boolean(checkedDate && health?.last_market_sync && checkedDate !== health.last_market_sync);
  const totalMoves = (overview?.advancers ?? 0) + (overview?.decliners ?? 0);
  const advancingShare = totalMoves > 0 ? ((overview?.advancers ?? 0) / totalMoves) * 100 : 50;

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />

      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                Welcome back{user ? `, ${user.display_name}` : ""}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Here&apos;s an overview of the research universe available to you.
              </p>
            </div>
            {health && (isDemoData ? (
              <Badge variant="secondary" className="gap-1.5 border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400">
                <Sparkles className="h-3.5 w-3.5" />
                DEMO DATA &mdash; not real market data
              </Badge>
            ) : (
              <Badge variant="secondary" className="gap-1.5 border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                <Clock className="h-3.5 w-3.5" />
                {dataIsBehindLastCheck
                  ? `Live NSE data — prices as of ${formatDate(health.last_market_sync)} (checked ${formatDate(checkedDate)}, no new trading data - likely a holiday)`
                  : `Live NSE data — last synced ${formatDate(health.last_market_sync)}`}
              </Badge>
            ))}
          </div>

          {adminNote && adminNote.message.trim() && (
            <Card className="border-blue-500/30 bg-blue-500/5">
              <CardContent className="flex items-start gap-3 pt-6">
                <Megaphone className="mt-0.5 h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400" />
                <div className="space-y-1.5">
                  <p className="text-sm font-medium">Note from the StockAI team</p>
                  <p className="text-sm whitespace-pre-wrap text-foreground">{adminNote.message}</p>
                  <p className="text-xs text-muted-foreground">{brand.adminNoteDisclaimer}</p>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Companies tracked</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-semibold">
                {isLoading ? <Skeleton className="h-9 w-16" /> : companies.length}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Sectors covered</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-semibold">
                {isLoading ? <Skeleton className="h-9 w-16" /> : sectorCount}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Market movers</CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <Skeleton className="h-9 w-24" />
                ) : (
                  <>
                    <div className="flex items-baseline justify-between text-sm font-semibold">
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <TrendingUp className="h-3.5 w-3.5" /> {overview?.advancers ?? 0}
                      </span>
                      <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                        {overview?.decliners ?? 0} <TrendingDown className="h-3.5 w-3.5" />
                      </span>
                    </div>
                    <div className="mt-2 flex h-1.5 w-full overflow-hidden rounded-full bg-red-500/20">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${advancingShare}%` }}
                      />
                    </div>
                    <p className="mt-1.5 text-xs text-muted-foreground">Advancing vs declining today</p>
                  </>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">AI provider</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-semibold capitalize">
                {isLoading ? <Skeleton className="h-9 w-16" /> : health?.ai_provider}
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Stock universe</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative mb-3">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search by symbol, name or sector..."
                    className="pl-9"
                  />
                </div>

                {overview && overview.sector_breakdown.length > 0 && (
                  <div className="mb-4 flex flex-wrap gap-1.5">
                    <button
                      onClick={() => setSelectedSector(null)}
                      className={cn(
                        "rounded-full border px-2.5 py-1 text-xs transition-colors",
                        selectedSector === null
                          ? "border-primary bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent",
                      )}
                    >
                      All sectors
                    </button>
                    {overview.sector_breakdown.map((s) => (
                      <button
                        key={s.sector}
                        onClick={() => setSelectedSector((prev) => (prev === s.sector ? null : s.sector))}
                        className={cn(
                          "rounded-full border px-2.5 py-1 text-xs transition-colors",
                          selectedSector === s.sector
                            ? "border-primary bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent",
                        )}
                      >
                        {s.sector} <span className="opacity-70">({s.count})</span>
                      </button>
                    ))}
                  </div>
                )}

                {isLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Company</TableHead>
                          <TableHead className="hidden sm:table-cell">Sector</TableHead>
                          <TableHead className="hidden md:table-cell">Exchange</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {visibleCompanies.map((company) => (
                          <TableRow
                            key={company.id}
                            className="cursor-pointer select-none"
                            onClick={() => router.push(`/stocks/${company.symbol}`)}
                          >
                            <TableCell className="font-medium">{company.symbol}</TableCell>
                            <TableCell>{company.name}</TableCell>
                            <TableCell className="hidden text-muted-foreground sm:table-cell">
                              {company.sector}
                            </TableCell>
                            <TableCell className="hidden text-muted-foreground md:table-cell">
                              {company.exchange}
                            </TableCell>
                          </TableRow>
                        ))}
                        {filteredCompanies.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-center text-muted-foreground">
                              No companies match your search.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                )}
                <Pagination page={page} totalItems={filteredCompanies.length} onPageChange={setPage} />
                <p className="mt-3 text-xs text-muted-foreground">
                  Click a company to open its research page with charts, financials and technicals.
                </p>
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Bot className="h-4 w-4" /> Quick AI research
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => router.push(`/research?q=${encodeURIComponent(prompt)}`)}
                      className="w-full rounded-md border border-dashed px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                    >
                      {prompt}
                    </button>
                  ))}
                  <p className="pt-1 text-xs text-muted-foreground">
                    Answers are grounded in real computed metrics - never buy/sell instructions.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ListChecks className="h-4 w-4" /> Watchlist
                  </CardTitle>
                  {watchlist.length > 0 && (
                    <Button asChild variant="ghost" size="sm" className="h-7 text-xs">
                      <Link href="/watchlist">View all</Link>
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {watchlist.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Your watchlist is empty.{" "}
                      <Link href="/watchlist" className="underline underline-offset-2">
                        Add a stock
                      </Link>{" "}
                      to track it here.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {watchlist.slice(0, 4).map((item) => (
                        <button
                          key={item.symbol}
                          onClick={() => router.push(`/stocks/${item.symbol}`)}
                          className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                        >
                          <span>
                            <span className="font-medium">{item.symbol}</span>{" "}
                            <span
                              className={
                                (item.change_percent ?? 0) >= 0
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : "text-red-600 dark:text-red-400"
                              }
                            >
                              {formatPercent(item.change_percent)}
                            </span>
                          </span>
                          <span className="flex items-center gap-2">
                            <span className="tabular-nums text-muted-foreground">
                              {formatPrice(item.latest_price)}
                            </span>
                            <AIScoreBadge score={item.ai_score} label={item.ai_label} />
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {overview && (overview.top_gainers.length > 0 || overview.top_losers.length > 0) && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <MoverList
                title="Top Gainers"
                icon={TrendingUp}
                tone="up"
                stocks={overview.top_gainers}
                onSelect={(symbol) => router.push(`/stocks/${symbol}`)}
              />
              <MoverList
                title="Top Losers"
                icon={TrendingDown}
                tone="down"
                stocks={overview.top_losers}
                onSelect={(symbol) => router.push(`/stocks/${symbol}`)}
              />
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
