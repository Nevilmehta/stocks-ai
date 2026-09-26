"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Filter, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

import { AIScoreBadge } from "@/components/ai-score-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { api } from "@/lib/api";
import { formatNumber, formatPercent, formatPrice } from "@/lib/format";
import type { Company, ScreenerFilters, ScreenerRow } from "@/types";

const EMPTY_FILTERS: ScreenerFilters = {};

const EXAMPLE_PRESET: ScreenerFilters = { roe_min: 15, debt_to_equity_max: 0.5, revenue_growth_min: 10 };

function FilterField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  placeholder: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(event) => {
          const raw = event.target.value;
          onChange(raw === "" ? undefined : Number(raw));
        }}
      />
    </div>
  );
}

export default function ScreenerPage() {
  const router = useRouter();
  const [sectors, setSectors] = useState<string[]>([]);
  const [filters, setFilters] = useState<ScreenerFilters>(EMPTY_FILTERS);
  const [rows, setRows] = useState<ScreenerRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<Company[]>("/api/stocks").then((companies) => {
      setSectors(Array.from(new Set(companies.map((c) => c.sector))).sort());
    });
  }, []);

  // Guards against a slower, superseded request resolving after a newer one
  // and clobbering its results (e.g. rapid filter changes, or React Strict
  // Mode's double-invoked mount effect racing the first real request).
  const requestIdRef = useRef(0);

  const runScreener = (nextFilters: ScreenerFilters) => {
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    const params = new URLSearchParams();
    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") params.set(key, String(value));
    });
    api
      .get<ScreenerRow[]>(`/api/screener?${params.toString()}`)
      .then((data) => {
        if (requestIdRef.current === requestId) setRows(data);
      })
      .catch(() => toast.error("Failed to run screener."))
      .finally(() => {
        if (requestIdRef.current === requestId) setIsLoading(false);
      });
  };

  useEffect(() => {
    runScreener(EMPTY_FILTERS);
  }, []);

  const setField = (key: keyof ScreenerFilters, value: number | string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const activeFilterCount = useMemo(
    () => Object.values(filters).filter((v) => v !== undefined && v !== "").length,
    [filters],
  );

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Stock screener</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Filter the research universe by fundamentals and AI Research Score.
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <SlidersHorizontal className="h-4 w-4" /> Filters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
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
                <FilterField
                  label="Market cap min (Cr)"
                  value={filters.market_cap_min}
                  onChange={(v) => setField("market_cap_min", v)}
                  placeholder="e.g. 50000"
                />
                <FilterField
                  label="P/E max"
                  value={filters.pe_max}
                  onChange={(v) => setField("pe_max", v)}
                  placeholder="e.g. 30"
                />
                <FilterField
                  label="ROE min (%)"
                  value={filters.roe_min}
                  onChange={(v) => setField("roe_min", v)}
                  placeholder="e.g. 15"
                />
                <FilterField
                  label="ROCE min (%)"
                  value={filters.roce_min}
                  onChange={(v) => setField("roce_min", v)}
                  placeholder="e.g. 15"
                />
                <FilterField
                  label="Debt/Equity max"
                  value={filters.debt_to_equity_max}
                  onChange={(v) => setField("debt_to_equity_max", v)}
                  placeholder="e.g. 0.5"
                />
                <FilterField
                  label="Revenue growth min (%)"
                  value={filters.revenue_growth_min}
                  onChange={(v) => setField("revenue_growth_min", v)}
                  placeholder="e.g. 10"
                />
                <FilterField
                  label="Profit growth min (%)"
                  value={filters.profit_growth_min}
                  onChange={(v) => setField("profit_growth_min", v)}
                  placeholder="e.g. 10"
                />
                <FilterField
                  label="AI Score min"
                  value={filters.ai_score_min}
                  onChange={(v) => setField("ai_score_min", v)}
                  placeholder="e.g. 60"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button size="sm" onClick={() => runScreener(filters)} className="gap-1.5">
                  <Filter className="h-3.5 w-3.5" /> Apply filters {activeFilterCount > 0 && `(${activeFilterCount})`}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setFilters(EMPTY_FILTERS);
                    runScreener(EMPTY_FILTERS);
                  }}
                >
                  Reset
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-auto max-w-full min-w-0 justify-start py-1.5 text-left whitespace-normal"
                  onClick={() => {
                    setFilters(EXAMPLE_PRESET);
                    runScreener(EXAMPLE_PRESET);
                  }}
                >
                  <span className="sm:hidden">Example preset</span>
                  <span className="hidden sm:inline">Example: ROE &gt; 15%, D/E &lt; 0.5, Rev growth &gt; 10%</span>
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
                  No companies match these filters. Try loosening a threshold.
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
                        <TableHead className="text-right">P/E</TableHead>
                        <TableHead className="text-right">ROE</TableHead>
                        <TableHead className="text-right">Rev. growth</TableHead>
                        <TableHead>AI Score</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rows.map((row) => (
                        <TableRow
                          key={row.symbol}
                          className="cursor-pointer select-none"
                          onClick={() => router.push(`/stocks/${row.symbol}`)}
                        >
                          <TableCell className="font-medium">{row.symbol}</TableCell>
                          <TableCell className="text-muted-foreground">{row.name}</TableCell>
                          <TableCell className="hidden text-muted-foreground md:table-cell">{row.sector}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPrice(row.latest_price)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatNumber(row.pe_ratio)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(row.roe)}</TableCell>
                          <TableCell className="text-right tabular-nums">{formatPercent(row.revenue_growth)}</TableCell>
                          <TableCell>
                            <AIScoreBadge score={row.ai_score} label={row.ai_label} />
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
