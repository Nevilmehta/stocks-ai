"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ExternalLink, Filter, Minus, SlidersHorizontal, TrendingDown, TrendingUp, Zap } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
import { Pagination, PAGE_SIZE } from "@/components/pagination";
import { brand } from "@/config/brand";
import { api } from "@/lib/api";
import { formatCompactVolume, formatNumber, formatPercent, formatPrice } from "@/lib/format";
import type { Company, SmartIndicatorFilters, SmartIndicatorMeta, SmartIndicatorRow, TradeSignal } from "@/types";

const EMPTY_FILTERS: SmartIndicatorFilters = {};

function SignalBadge({ signal, reasons }: { signal: TradeSignal; reasons: string[] }) {
  const style =
    signal === "buy"
      ? { Icon: TrendingUp, classes: "text-emerald-600 dark:text-emerald-400", label: "Buy" }
      : signal === "sell"
        ? { Icon: TrendingDown, classes: "text-red-600 dark:text-red-400", label: "Sell" }
        : { Icon: Minus, classes: "text-muted-foreground", label: "Neutral" };
  const { Icon, classes, label } = style;

  return (
    <div title={reasons.join(", ")} className={`flex items-center gap-1.5 font-medium ${classes}`}>
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </div>
  );
}

export default function SmartIndicatorPage() {
  const router = useRouter();
  const [sectors, setSectors] = useState<string[]>([]);
  const [meta, setMeta] = useState<SmartIndicatorMeta | null>(null);
  const [filters, setFilters] = useState<SmartIndicatorFilters>(EMPTY_FILTERS);
  const [rows, setRows] = useState<SmartIndicatorRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    api.get<Company[]>("/api/stocks").then((companies) => {
      setSectors(Array.from(new Set(companies.map((c) => c.sector))).sort());
    });
    api
      .get<SmartIndicatorMeta>("/api/smart-indicator/meta")
      .then((data) => {
        setMeta(data);
        // Only admin-enabled indicators are ever offered - customers can
        // switch between those, never add one admin hasn't turned on.
        setFilters((prev) => ({ ...prev, indicator: prev.indicator ?? data.default_indicator }));
      })
      .catch(() => toast.error("Failed to load available indicators."));
  }, []);

  // Same race-guard pattern as the screener page: a slower, superseded
  // request resolving after a newer one must not clobber its results.
  const requestIdRef = useRef(0);

  const runQuery = (nextFilters: SmartIndicatorFilters) => {
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    const params = new URLSearchParams();
    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") params.set(key, String(value));
    });
    api
      .get<SmartIndicatorRow[]>(`/api/smart-indicator?${params.toString()}`)
      .then((data) => {
        if (requestIdRef.current === requestId) {
          setRows(data);
          setPage(1);
        }
      })
      .catch(() => toast.error("Failed to load smart indicator results."))
      .finally(() => {
        if (requestIdRef.current === requestId) setIsLoading(false);
      });
  };

  // Waits for /meta to resolve the default indicator before the first query,
  // so the initial load already shows the admin's chosen default view.
  useEffect(() => {
    if (meta) runQuery(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta]);

  const setField = <K extends keyof SmartIndicatorFilters>(key: K, value: SmartIndicatorFilters[K] | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const selectIndicator = (key: SmartIndicatorFilters["indicator"]) => {
    const next = { ...filters, indicator: key };
    setFilters(next);
    runQuery(next);
  };

  const indicatorValueLabel = rows[0]?.indicator_label ?? "Indicator";
  const pageRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
              <Zap className="h-5 w-5" /> Smart Indicator
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Every tracked stock filtered against the active indicator strategy - RSI, trend, swing
              structure (higher highs/lower lows) and Fibonacci retracement.
            </p>
          </div>

          {meta && meta.available_indicators.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {meta.available_indicators.map((option) => (
                <Button
                  key={option.key}
                  size="sm"
                  variant={filters.indicator === option.key ? "default" : "outline"}
                  onClick={() => selectIndicator(option.key)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <SlidersHorizontal className="h-4 w-4" /> Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Sector</Label>
                  <Select
                    value={filters.sector ?? "all"}
                    onValueChange={(value) => setField("sector", value === "all" ? undefined : value)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="All sectors" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All sectors</SelectItem>
                      {sectors.map((sector) => (
                        <SelectItem key={sector} value={sector}>
                          {sector}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Signal</Label>
                  <Select
                    value={filters.signal ?? "all"}
                    onValueChange={(value) =>
                      setField("signal", value === "all" ? undefined : (value as TradeSignal))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Any signal" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Any signal</SelectItem>
                      <SelectItem value="buy">Buy</SelectItem>
                      <SelectItem value="sell">Sell</SelectItem>
                      <SelectItem value="neutral">Neutral</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">RSI</Label>
                  <Select
                    value={filters.rsi_state ?? "any"}
                    onValueChange={(value) =>
                      setField("rsi_state", value === "any" ? undefined : (value as "oversold" | "overbought"))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Any" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any</SelectItem>
                      <SelectItem value="oversold">Oversold</SelectItem>
                      <SelectItem value="overbought">Overbought</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Swing structure</Label>
                  <Select
                    value={filters.trend_structure ?? "any"}
                    onValueChange={(value) =>
                      setField(
                        "trend_structure",
                        value === "any" ? undefined : (value as "uptrend" | "downtrend" | "sideways"),
                      )
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Any" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any</SelectItem>
                      <SelectItem value="uptrend">Uptrend</SelectItem>
                      <SelectItem value="downtrend">Downtrend</SelectItem>
                      <SelectItem value="sideways">Sideways</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button size="sm" onClick={() => runQuery(filters)} className="gap-1.5">
                  <Filter className="h-3.5 w-3.5" /> Apply filters
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const next = { ...EMPTY_FILTERS, indicator: filters.indicator };
                    setFilters(next);
                    runQuery(next);
                  }}
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Results{isLoading ? "" : ` (${rows.length})`}</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : rows.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No companies match these filters. Try loosening them.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Symbol</TableHead>
                        <TableHead>Company</TableHead>
                        <TableHead className="hidden md:table-cell">Sector</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead className="text-right">Volume</TableHead>
                        <TableHead className="text-right">1D Return</TableHead>
                        <TableHead className="text-right">1W Return</TableHead>
                        <TableHead className="text-right">1M Return</TableHead>
                        <TableHead className="text-right">P/E</TableHead>
                        <TableHead className="text-right">{indicatorValueLabel}</TableHead>
                        <TableHead>Signal</TableHead>
                        <TableHead>Trade</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pageRows.map((row) => (
                        <TableRow
                          key={row.symbol}
                          className="cursor-pointer select-none"
                          onClick={() => router.push(`/stocks/${row.symbol}`)}
                        >
                          <TableCell className="font-medium">{row.symbol}</TableCell>
                          <TableCell className="text-muted-foreground">{row.name}</TableCell>
                          <TableCell className="hidden text-muted-foreground md:table-cell">{row.sector}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPrice(row.latest_price)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatCompactVolume(row.volume)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(row.return_1d)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(row.return_1w)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(row.return_1m)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatNumber(row.pe_ratio)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatNumber(row.indicator_value)}</TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <SignalBadge signal={row.signal} reasons={row.signal_reasons} />
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <a
                              href={brand.angelOneUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Opens Angel One in a new tab - StockAI is not affiliated with Angel One and does not execute trades."
                              className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                            >
                              Angel One <ExternalLink className="h-3 w-3" />
                            </a>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Pagination page={page} totalItems={rows.length} onPageChange={setPage} />
                </div>
              )}
            </CardContent>
          </Card>

          <p className="text-xs leading-relaxed text-muted-foreground">{brand.smartIndicatorDisclaimer}</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
