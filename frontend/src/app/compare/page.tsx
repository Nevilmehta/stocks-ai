"use client";

import { useEffect, useState } from "react";
import { Bot, Loader2, Scale } from "lucide-react";
import { toast } from "sonner";

import { AIScoreBadge } from "@/components/ai-score-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CompareChart } from "@/components/compare-chart";
import { MarkdownContent } from "@/components/markdown-content";
import { StockPicker } from "@/components/stock-picker";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { ApiError, api } from "@/lib/api";
import { formatCrore, formatNumber, formatPercent, formatPrice } from "@/lib/format";
import type { Company, CompareResponse, CompareRow } from "@/types";

interface MetricRow {
  label: string;
  render: (row: CompareRow) => string;
}

const METRIC_ROWS: MetricRow[] = [
  { label: "Latest price", render: (r) => formatPrice(r.latest_price) },
  { label: "Change %", render: (r) => formatPercent(r.change_percent) },
  { label: "Market cap", render: (r) => formatCrore(r.market_cap) },
  { label: "P/E", render: (r) => formatNumber(r.pe_ratio) },
  { label: "P/B", render: (r) => formatNumber(r.pb_ratio) },
  { label: "ROE", render: (r) => formatPercent(r.roe) },
  { label: "ROCE", render: (r) => formatPercent(r.roce) },
  { label: "Debt/Equity", render: (r) => formatNumber(r.debt_to_equity) },
  { label: "Revenue growth", render: (r) => formatPercent(r.revenue_growth) },
  { label: "Profit growth", render: (r) => formatPercent(r.profit_growth) },
  { label: "Technical momentum", render: (r) => formatNumber(r.technical_momentum, 0) },
];

export default function ComparePage() {
  const [selected, setSelected] = useState<Company[]>([]);
  const [data, setData] = useState<CompareResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [aiText, setAiText] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);

  useEffect(() => {
    setAiText(null);
    if (selected.length < 2) {
      setData(null);
      return;
    }
    // Guards against a slower, superseded request (e.g. the previous
    // selection) resolving after a newer one and showing a stale comparison.
    let cancelled = false;
    setIsLoading(true);
    api
      .post<CompareResponse>("/api/compare", { symbols: selected.map((c) => c.symbol) })
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch((error) => {
        if (!cancelled) toast.error(error instanceof ApiError ? error.message : "Failed to compare.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const handleAiCompare = async () => {
    setIsAiLoading(true);
    try {
      const response = await api.post<{ text: string }>("/api/compare/ai", {
        symbols: selected.map((c) => c.symbol),
      });
      setAiText(response.text);
    } catch {
      toast.error("Failed to generate AI comparison.");
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-5xl space-y-6 px-4 py-10 sm:px-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Compare stocks</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Select 2-3 companies to compare fundamentals, technicals, and AI Research Score.
            </p>
          </div>

          <Card>
            <CardContent className="pt-6">
              <StockPicker selected={selected} onChange={setSelected} max={3} />
            </CardContent>
          </Card>

          {selected.length < 2 && (
            <p className="text-center text-sm text-muted-foreground">
              Add at least 2 companies to see a comparison.
            </p>
          )}

          {isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-[320px] w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}

          {data && !isLoading && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Price performance (1Y)</CardTitle>
                </CardHeader>
                <CardContent>
                  <CompareChart rows={data.rows} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Comparison</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Metric</th>
                        {data.rows.map((row) => (
                          <th key={row.symbol} className="py-2 pr-4 font-medium text-foreground">
                            {row.symbol}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b">
                        <td className="py-2 pr-4 text-muted-foreground">AI Research Score</td>
                        {data.rows.map((row) => (
                          <td key={row.symbol} className="py-2 pr-4">
                            <AIScoreBadge score={row.ai_score} label={row.ai_label} />
                          </td>
                        ))}
                      </tr>
                      <tr className="border-b">
                        <td className="py-2 pr-4 text-muted-foreground">Risk</td>
                        {data.rows.map((row) => (
                          <td key={row.symbol} className="py-2 pr-4">
                            {row.risk_label ?? "Data unavailable"}
                          </td>
                        ))}
                      </tr>
                      {METRIC_ROWS.map((metric) => (
                        <tr key={metric.label} className="border-b last:border-0">
                          <td className="py-2 pr-4 text-muted-foreground">{metric.label}</td>
                          {data.rows.map((row) => (
                            <td key={row.symbol} className="py-2 pr-4 tabular-nums">
                              {metric.render(row)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Scale className="h-4 w-4" /> AI Compare
                  </CardTitle>
                  <Button size="sm" onClick={handleAiCompare} disabled={isAiLoading} className="gap-1.5">
                    {isAiLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
                    Generate
                  </Button>
                </CardHeader>
                <CardContent>
                  {aiText ? (
                    <MarkdownContent content={aiText} className="text-muted-foreground" />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Click Generate for an AI-written comparison grounded in the exact numbers above -
                      never a recommendation to buy or sell.
                    </p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
