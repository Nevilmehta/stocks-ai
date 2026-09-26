"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ListPlus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { AIScoreBadge } from "@/components/ai-score-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { ApiError, api } from "@/lib/api";
import { formatNumber, formatPercent, formatPrice } from "@/lib/format";
import type { Company, WatchlistItem } from "@/types";

export default function WatchlistPage() {
  const router = useRouter();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [addingSymbol, setAddingSymbol] = useState<string | null>(null);
  const [removingSymbol, setRemovingSymbol] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadWatchlist = () => {
    setIsLoading(true);
    api
      .get<WatchlistItem[]>("/api/watchlist")
      .then(setItems)
      .catch(() => toast.error("Failed to load watchlist."))
      .finally(() => setIsLoading(false));
  };

  useEffect(loadWatchlist, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length === 0) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    debounceRef.current = setTimeout(() => {
      api
        .get<Company[]>(`/api/stocks/search?q=${encodeURIComponent(query.trim())}`)
        .then(setResults)
        .finally(() => setIsSearching(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const watchlistSymbols = new Set(items.map((i) => i.symbol));

  const handleAdd = async (symbol: string) => {
    setAddingSymbol(symbol);
    try {
      const item = await api.post<WatchlistItem>("/api/watchlist", { symbol });
      setItems((prev) => [item, ...prev]);
      setQuery("");
      setResults([]);
      toast.success(`${symbol} added to watchlist`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to add to watchlist.");
    } finally {
      setAddingSymbol(null);
    }
  };

  const handleRemove = async (symbol: string) => {
    setRemovingSymbol(symbol);
    try {
      await api.delete(`/api/watchlist/${symbol}`);
      setItems((prev) => prev.filter((i) => i.symbol !== symbol));
    } catch {
      toast.error("Failed to remove from watchlist.");
    } finally {
      setRemovingSymbol(null);
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-5xl space-y-6 px-4 py-10 sm:px-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Watchlist</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Track companies you&apos;re researching with live-refreshed key metrics.
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ListPlus className="h-4 w-4" /> Add a stock
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Popover open={query.trim().length > 0}>
                <PopoverAnchor asChild>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Search by symbol, name or sector..."
                      className="pl-9"
                    />
                  </div>
                </PopoverAnchor>
                <PopoverContent
                  align="start"
                  onOpenAutoFocus={(event) => event.preventDefault()}
                  className="w-[var(--radix-popper-anchor-width)] p-1"
                >
                  {isSearching ? (
                    <div className="flex items-center justify-center py-3">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : results.length === 0 ? (
                    <p className="px-2 py-3 text-center text-sm text-muted-foreground">No matches.</p>
                  ) : (
                    results.map((company) => {
                      const alreadyAdded = watchlistSymbols.has(company.symbol);
                      return (
                        <button
                          key={company.symbol}
                          disabled={alreadyAdded || addingSymbol === company.symbol}
                          onClick={() => handleAdd(company.symbol)}
                          className="flex w-full items-center justify-between rounded-md px-3 py-1.5 text-left text-sm hover:bg-accent disabled:opacity-50"
                        >
                          <span>
                            <span className="font-medium">{company.symbol}</span>{" "}
                            <span className="text-muted-foreground">&middot; {company.name}</span>
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {alreadyAdded ? "Added" : addingSymbol === company.symbol ? "Adding..." : "Add"}
                          </span>
                        </button>
                      );
                    })
                  )}
                </PopoverContent>
              </Popover>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Your watchlist ({items.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : items.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Your watchlist is empty. Search above or visit a{" "}
                  <Link href="/dashboard" className="underline underline-offset-2">
                    stock page
                  </Link>{" "}
                  to add one.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Symbol</TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead className="text-right">Change</TableHead>
                        <TableHead className="text-right">P/E</TableHead>
                        <TableHead className="text-right">ROE</TableHead>
                        <TableHead>AI Score</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {items.map((item) => (
                        <TableRow
                          key={item.symbol}
                          className="cursor-pointer select-none"
                          onClick={() => router.push(`/stocks/${item.symbol}`)}
                        >
                          <TableCell className="font-medium">{item.symbol}</TableCell>
                          <TableCell className="text-muted-foreground">{item.name}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPrice(item.latest_price)}</TableCell>
                          <TableCell
                            className={
                              "text-right tabular-nums " +
                              ((item.change_percent ?? 0) >= 0
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-red-600 dark:text-red-400")
                            }
                          >
                            {formatPercent(item.change_percent)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{formatNumber(item.pe_ratio)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(item.roe)}</TableCell>
                          <TableCell>
                            <AIScoreBadge score={item.ai_score} label={item.ai_label} />
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="icon"
                              variant="ghost"
                              disabled={removingSymbol === item.symbol}
                              onClick={(event) => {
                                event.stopPropagation();
                                handleRemove(item.symbol);
                              }}
                            >
                              {removingSymbol === item.symbol ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4 text-destructive" />
                              )}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
      <Footer />
    </div>
  );
}
