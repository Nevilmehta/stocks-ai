"use client";

import { use, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  ListPlus,
  Loader2,
  ListCheck,
  Minus,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { AIIndicator } from "@/components/ai-indicator";
import { FinancialBarChart } from "@/components/financial-bar-chart";
import { StockChart } from "@/components/stock-chart";
import { brand } from "@/config/brand";
import { ApiError, api } from "@/lib/api";
import { formatCompactVolume, formatCrore, formatDate, formatNumber, formatPercent, formatPrice } from "@/lib/format";
import type {
  AIAnalysis,
  AIScore,
  Company,
  FinancialPeriod,
  HealthStatus,
  IntradayHistory,
  PeriodType,
  PricePoint,
  StockDetail,
  TechnicalIndicators,
  TimeRange,
} from "@/types";

const RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MAX"];

function sentimentClasses(label: string): string {
  if (label === "Positive") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
  if (label === "Negative") return "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400";
  return "border-muted-foreground/20 bg-muted text-muted-foreground";
}

function swingStructureClasses(structure: string): string {
  if (structure.startsWith("Uptrend")) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
  if (structure.startsWith("Downtrend")) return "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400";
  return "border-muted-foreground/20 bg-muted text-muted-foreground";
}

function SignalRow({ signal, reasons }: { signal: string; reasons: string[] }) {
  const style =
    signal === "buy"
      ? { Icon: TrendingUp, classes: "text-emerald-600 dark:text-emerald-400", label: "Buy" }
      : signal === "sell"
        ? { Icon: TrendingDown, classes: "text-red-600 dark:text-red-400", label: "Sell" }
        : { Icon: Minus, classes: "text-muted-foreground", label: "Neutral" };
  const { Icon, classes, label } = style;

  return (
    <div className="flex items-center justify-between" title={reasons.join(", ")}>
      <span className="text-sm text-muted-foreground">Signal</span>
      <span className={`flex items-center gap-1.5 font-medium ${classes}`}>
        <Icon className="h-4 w-4" /> {label}
      </span>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b py-2.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

export default function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol: rawSymbol } = use(params);
  const symbol = rawSymbol.toUpperCase();

  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [technicals, setTechnicals] = useState<TechnicalIndicators | null>(null);
  const [financials, setFinancials] = useState<FinancialPeriod[]>([]);
  const [aiScore, setAiScore] = useState<AIScore | null>(null);
  const [peers, setPeers] = useState<Company[]>([]);
  const [range, setRange] = useState<TimeRange>("1Y");
  const [showIntraday, setShowIntraday] = useState(false);
  const [intraday, setIntraday] = useState<IntradayHistory | null>(null);
  const [isIntradayLoading, setIsIntradayLoading] = useState(false);
  const [periodType, setPeriodType] = useState<PeriodType>("annual");
  const [notFound, setNotFound] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [inWatchlist, setInWatchlist] = useState(false);
  const [isTogglingWatchlist, setIsTogglingWatchlist] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    setNotFound(false);
    Promise.all([
      api.get<StockDetail>(`/api/stocks/${symbol}`),
      api.get<TechnicalIndicators>(`/api/stocks/${symbol}/technicals`),
      api.get<FinancialPeriod[]>(`/api/stocks/${symbol}/financials`),
      api.get<HealthStatus>("/api/health"),
      api.get<Company[]>(`/api/stocks/${symbol}/peers`),
      api.get<AIScore>(`/api/stocks/${symbol}/ai-score`).catch(() => null),
      api.get<{ symbol: string }[]>("/api/watchlist").catch(() => []),
    ])
      .then(([detailData, technicalsData, financialsData, healthData, peerCompanies, aiScoreData, watchlistItems]) => {
        setDetail(detailData);
        setTechnicals(technicalsData);
        setFinancials(financialsData);
        setHealth(healthData);
        setAiScore(aiScoreData);
        setPeers(peerCompanies);
        setInWatchlist(watchlistItems.some((item) => item.symbol === symbol));
      })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          setNotFound(true);
        } else {
          toast.error("Failed to load stock data.");
        }
      })
      .finally(() => setIsLoading(false));
  }, [symbol]);

  useEffect(() => {
    if (notFound) return;
    // Guards against a slower, superseded request (e.g. a previous range
    // button click) resolving after a newer one and showing stale data
    // under the currently-selected range.
    let cancelled = false;
    setIsHistoryLoading(true);
    api
      .get<PricePoint[]>(`/api/stocks/${symbol}/history?range=${range}`)
      .then((data) => {
        if (!cancelled) setHistory(data);
      })
      .catch(() => {
        if (!cancelled) toast.error("Failed to load price history.");
      })
      .finally(() => {
        if (!cancelled) setIsHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, range, notFound]);

  useEffect(() => {
    if (notFound || !showIntraday) return;
    let cancelled = false;
    setIsIntradayLoading(true);
    api
      .get<IntradayHistory>(`/api/stocks/${symbol}/intraday`)
      .then((data) => {
        if (!cancelled) setIntraday(data);
      })
      .catch(() => {
        if (!cancelled) toast.error("Failed to load intraday data.");
      })
      .finally(() => {
        if (!cancelled) setIsIntradayLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, showIntraday, notFound]);

  useEffect(() => {
    setAiAnalysis(null);
  }, [symbol]);

  const handleAnalyse = async () => {
    setIsAnalysing(true);
    setActiveTab("ai");
    try {
      const analysis = await api.post<AIAnalysis>("/api/research/analyse", { symbol });
      setAiAnalysis(analysis);
    } catch {
      toast.error("Failed to generate AI analysis.");
    } finally {
      setIsAnalysing(false);
    }
  };

  const handleToggleWatchlist = async () => {
    setIsTogglingWatchlist(true);
    try {
      if (inWatchlist) {
        await api.delete(`/api/watchlist/${symbol}`);
        setInWatchlist(false);
        toast.success(`${symbol} removed from watchlist`);
      } else {
        await api.post("/api/watchlist", { symbol });
        setInWatchlist(true);
        toast.success(`${symbol} added to watchlist`);
      }
    } catch {
      toast.error("Failed to update watchlist.");
    } finally {
      setIsTogglingWatchlist(false);
    }
  };

  const visibleFinancials = useMemo(
    () => financials.filter((f) => f.period_type === periodType),
    [financials, periodType],
  );

  const isDemoData = health?.market_data_provider === "mock";
  const isUp = (detail?.change ?? 0) >= 0;

  if (notFound) {
    return (
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main className="flex flex-1 items-center justify-center px-4">
          <Card className="max-w-md text-center">
            <CardHeader>
              <CardTitle>Stock not found</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                We couldn&apos;t find &quot;{symbol}&quot; in the research universe.
              </p>
              <Button asChild className="mt-4">
                <Link href="/dashboard">Back to dashboard</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <Navbar />
      <main className="flex-1 bg-muted/20">
        <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Dashboard
          </Link>

          {isLoading || !detail ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-72" />
              <Skeleton className="h-6 w-96" />
            </div>
          ) : (
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-semibold tracking-tight">{detail.name}</h1>
                  <Badge variant="secondary">{detail.symbol}</Badge>
                  <Badge variant="outline">{detail.exchange}</Badge>
                  {isDemoData && (
                    <Badge className="gap-1 border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400">
                      <Sparkles className="h-3 w-3" /> DEMO DATA
                    </Badge>
                  )}
                  {detail.index_memberships.map((index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {index}
                    </Badge>
                  ))}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {detail.sector} &middot; {detail.industry}
                </p>
                <div className="mt-3 flex items-baseline gap-3">
                  <span className="text-3xl font-semibold tabular-nums">{formatPrice(detail.latest_price)}</span>
                  {detail.change !== null && detail.change_percent !== null && (
                    <span
                      className={
                        "flex items-center gap-1 text-sm font-medium " +
                        (isUp ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400")
                      }
                    >
                      {isUp ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      {formatNumber(detail.change)} ({formatPercent(detail.change_percent)})
                    </span>
                  )}
                  {detail.as_of && <span className="text-xs text-muted-foreground">as of {detail.as_of}</span>}
                  {detail.volume !== null && (
                    <span className="text-xs text-muted-foreground">Vol: {formatCompactVolume(detail.volume)}</span>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant={inWatchlist ? "secondary" : "outline"}
                  onClick={handleToggleWatchlist}
                  disabled={isTogglingWatchlist}
                  className="gap-1.5"
                >
                  {isTogglingWatchlist ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : inWatchlist ? (
                    <ListCheck className="h-4 w-4" />
                  ) : (
                    <ListPlus className="h-4 w-4" />
                  )}
                  {inWatchlist ? "In Watchlist" : "Watchlist"}
                </Button>
                <Button onClick={handleAnalyse} disabled={isAnalysing} className="gap-1.5">
                  {isAnalysing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                  AI Analyse
                </Button>
                <Button asChild variant="outline" className="gap-1.5">
                  <a
                    href={brand.angelOneUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="StockAI is not affiliated with Angel One and does not execute trades."
                  >
                    Trade on Angel One <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </Button>
              </div>
            </div>
          )}

          <Card>
            <CardContent className="pt-6">
              <div className="mb-4 flex flex-wrap items-center gap-1.5">
                {RANGES.map((r) => (
                  <Button
                    key={r}
                    size="sm"
                    variant={!showIntraday && range === r ? "default" : "outline"}
                    className="h-7 px-2.5 text-xs"
                    onClick={() => {
                      setShowIntraday(false);
                      setRange(r);
                    }}
                  >
                    {r}
                  </Button>
                ))}
                <span className="mx-1 h-4 w-px bg-border" />
                <Button
                  size="sm"
                  variant={showIntraday ? "default" : "outline"}
                  className="h-7 gap-1 px-2.5 text-xs"
                  onClick={() => setShowIntraday(true)}
                  title="Real minute-by-minute chart for the most recent NSE trading session - free, unofficial data source, not available for every stock."
                >
                  <Clock className="h-3 w-3" /> Intraday
                </Button>
              </div>
              {showIntraday ? (
                isIntradayLoading ? (
                  <Skeleton className="h-[360px] w-full sm:h-[420px]" />
                ) : intraday && intraday.points.length > 0 ? (
                  <>
                    <p className="mb-2 text-xs text-muted-foreground">
                      Showing the {intraday.points.length}-minute session from {formatDate(intraday.trading_date)} -
                      minute data is fetched live from a free third-party source (not NSE directly) and may not be
                      available for every stock.
                    </p>
                    <StockChart
                      data={intraday.points.map((p) => ({
                        date: p.time,
                        open: p.open,
                        high: p.high,
                        low: p.low,
                        close: p.close,
                        volume: p.volume,
                      }))}
                      timeVisible
                    />
                  </>
                ) : (
                  <p className="flex h-[360px] items-center justify-center text-center text-sm text-muted-foreground sm:h-[420px]">
                    Intraday data isn&apos;t available for this stock right now.
                  </p>
                )
              ) : isHistoryLoading ? (
                <Skeleton className="h-[360px] w-full sm:h-[420px]" />
              ) : (
                <StockChart data={history} />
              )}
            </CardContent>
          </Card>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="financials">Financials</TabsTrigger>
              <TabsTrigger value="technicals">Technicals</TabsTrigger>
              <TabsTrigger value="ai">AI Analysis</TabsTrigger>
              <TabsTrigger value="peers">Peers</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <Card className="lg:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-base">About</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed text-muted-foreground">{detail?.description}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Key metrics</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <StatRow label="Market cap" value={formatCrore(detail?.market_cap)} />
                    <StatRow label="P/E" value={formatNumber(detail?.pe_ratio)} />
                    <StatRow label="P/B" value={formatNumber(detail?.pb_ratio)} />
                    <StatRow label="ROE" value={formatPercent(detail?.roe)} />
                    <StatRow label="ROCE" value={formatPercent(detail?.roce)} />
                    <StatRow label="EPS" value={formatPrice(detail?.eps)} />
                    <StatRow label="Debt/Equity" value={formatNumber(detail?.debt_to_equity)} />
                    <StatRow label="Revenue growth" value={formatPercent(detail?.revenue_growth)} />
                    <StatRow label="Profit growth" value={formatPercent(detail?.profit_growth)} />
                    <StatRow label="52-week high" value={formatPrice(detail?.week52_high)} />
                    <StatRow label="52-week low" value={formatPrice(detail?.week52_low)} />
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">AI Research Score</CardTitle>
                </CardHeader>
                <CardContent>
                  {aiScore ? (
                    <AIIndicator score={aiScore} />
                  ) : (
                    <p className="text-sm text-muted-foreground">Data unavailable.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="financials" className="space-y-6">
              <div className="flex gap-1.5">
                <Button
                  size="sm"
                  variant={periodType === "annual" ? "default" : "outline"}
                  onClick={() => setPeriodType("annual")}
                >
                  Annual
                </Button>
                <Button
                  size="sm"
                  variant={periodType === "quarterly" ? "default" : "outline"}
                  onClick={() => setPeriodType("quarterly")}
                >
                  Quarterly
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Revenue (Rs. Cr)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FinancialBarChart
                      data={visibleFinancials.map((f) => ({ label: f.period_label, value: f.revenue }))}
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Net profit (Rs. Cr)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FinancialBarChart
                      data={visibleFinancials.map((f) => ({ label: f.period_label, value: f.net_profit }))}
                    />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">EPS (Rs.)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <FinancialBarChart
                      data={visibleFinancials.map((f) => ({ label: f.period_label, value: f.eps }))}
                    />
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Period detail</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Period</th>
                        <th className="py-2 pr-4 font-medium">Revenue</th>
                        <th className="py-2 pr-4 font-medium">Net profit</th>
                        <th className="py-2 pr-4 font-medium">Op. profit</th>
                        <th className="py-2 pr-4 font-medium">EPS</th>
                        <th className="py-2 pr-4 font-medium">Cash flow</th>
                        <th className="py-2 pr-4 font-medium">Debt</th>
                        <th className="py-2 pr-4 font-medium">Net margin</th>
                        <th className="py-2 pr-4 font-medium">Rev. growth</th>
                        <th className="py-2 font-medium">Profit growth</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleFinancials.map((f) => (
                        <tr key={f.period_label} className="border-b last:border-0">
                          <td className="py-2 pr-4 font-medium">{f.period_label}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatCrore(f.revenue)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatCrore(f.net_profit)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatCrore(f.operating_profit)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatPrice(f.eps)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatCrore(f.operating_cash_flow)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatCrore(f.total_debt)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatPercent(f.net_margin)}</td>
                          <td className="py-2 pr-4 tabular-nums">{formatPercent(f.revenue_growth)}</td>
                          <td className="py-2 tabular-nums">{formatPercent(f.profit_growth)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="technicals" className="space-y-6">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Trend &amp; momentum</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Trend</span>
                      <Badge className={sentimentClasses(technicals?.trend ?? "")}>{technicals?.trend}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Momentum</span>
                      <Badge className={sentimentClasses(technicals?.momentum ?? "")}>{technicals?.momentum}</Badge>
                    </div>
                    {technicals && <SignalRow signal={technicals.signal} reasons={technicals.signal_reasons} />}
                    <StatRow label="RSI (14)" value={formatNumber(technicals?.rsi_14)} />
                    <StatRow label="MACD" value={formatNumber(technicals?.macd)} />
                    <StatRow label="MACD signal" value={formatNumber(technicals?.macd_signal)} />
                    <StatRow label="Price vs SMA 50" value={formatPercent(technicals?.price_vs_sma50_percent)} />
                    <StatRow label="Price vs SMA 200" value={formatPercent(technicals?.price_vs_sma200_percent)} />
                    <StatRow label="Volatility (annualized)" value={formatPercent(technicals?.volatility)} />
                    {technicals?.historical_oversold_forward_return && (
                      <p className="pt-1 text-xs text-muted-foreground">
                        Historically, after {technicals.historical_oversold_forward_return.occurrences} similar
                        oversold signals, this stock averaged{" "}
                        {formatPercent(technicals.historical_oversold_forward_return.avg_forward_return_30d)} over
                        the following 30 trading days. Past performance is not indicative of future results.
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Moving averages</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <StatRow label="SMA 20" value={formatPrice(technicals?.sma_20)} />
                    <StatRow label="SMA 50" value={formatPrice(technicals?.sma_50)} />
                    <StatRow label="SMA 200" value={formatPrice(technicals?.sma_200)} />
                    <StatRow label="EMA 20" value={formatPrice(technicals?.ema_20)} />
                    <StatRow label="EMA 50" value={formatPrice(technicals?.ema_50)} />
                    <StatRow label="EMA 200" value={formatPrice(technicals?.ema_200)} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Range &amp; returns</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <StatRow label="52-week high" value={formatPrice(technicals?.week52_high)} />
                    <StatRow label="52-week low" value={formatPrice(technicals?.week52_low)} />
                    <StatRow label="Bollinger upper" value={formatPrice(technicals?.bollinger_upper)} />
                    <StatRow label="Bollinger lower" value={formatPrice(technicals?.bollinger_lower)} />
                    <StatRow label="1M return" value={formatPercent(technicals?.return_1m)} />
                    <StatRow label="3M return" value={formatPercent(technicals?.return_3m)} />
                    <StatRow label="6M return" value={formatPercent(technicals?.return_6m)} />
                    <StatRow label="1Y return" value={formatPercent(technicals?.return_1y)} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Swing structure &amp; Fibonacci</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Structure</span>
                      <Badge className={swingStructureClasses(technicals?.swing_structure ?? "")}>
                        {technicals?.swing_structure}
                      </Badge>
                    </div>
                    <StatRow
                      label="Nearest Fibonacci level"
                      value={technicals?.nearest_fibonacci_level ?? "Data unavailable"}
                    />
                    <StatRow
                      label="Distance from level"
                      value={formatPercent(technicals?.nearest_fibonacci_distance_percent)}
                    />
                    {technicals?.fibonacci_levels && (
                      <div className="space-y-1 pt-2">
                        {Object.entries(technicals.fibonacci_levels).map(([name, value]) => (
                          <div key={name} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{name}</span>
                            <span className="tabular-nums">{formatPrice(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                Trend/momentum/moving-average/range figures are plain calculations from historical price
                data, shown as research framing only. {brand.smartIndicatorDisclaimer}
              </p>
            </TabsContent>

            <TabsContent value="ai" className="space-y-6">
              {isAnalysing ? (
                <Card>
                  <CardContent className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Generating research...
                  </CardContent>
                </Card>
              ) : aiAnalysis ? (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Summary</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-sm leading-relaxed">{aiAnalysis.summary}</p>
                      <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                        <div>
                          <p className="mb-1 font-medium">Financial Health</p>
                          <p className="text-muted-foreground">{aiAnalysis.financial_health}</p>
                        </div>
                        <div>
                          <p className="mb-1 font-medium">Growth</p>
                          <p className="text-muted-foreground">{aiAnalysis.growth}</p>
                        </div>
                        <div>
                          <p className="mb-1 font-medium">Profitability</p>
                          <p className="text-muted-foreground">{aiAnalysis.profitability}</p>
                        </div>
                        <div>
                          <p className="mb-1 font-medium">Valuation</p>
                          <p className="text-muted-foreground">{aiAnalysis.valuation}</p>
                        </div>
                        <div className="sm:col-span-2">
                          <p className="mb-1 font-medium">Technical Picture</p>
                          <p className="text-muted-foreground">{aiAnalysis.technical_picture}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Strengths
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                          {aiAnalysis.strengths.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" /> Risks
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                          {aiAnalysis.risks.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <Eye className="h-4 w-4 text-amber-600 dark:text-amber-400" /> Things to monitor
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                          {aiAnalysis.things_to_monitor.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>

                  <Card>
                    <CardContent className="space-y-3 pt-6">
                      <p className="text-sm font-medium">Conclusion</p>
                      <p className="text-sm text-muted-foreground">{aiAnalysis.conclusion}</p>
                      <p className="text-xs text-muted-foreground">{aiAnalysis.disclaimer}</p>
                    </CardContent>
                  </Card>
                </>
              ) : (
                <Card>
                  <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                    <Bot className="h-8 w-8 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Click &quot;AI Analyse&quot; above to generate research grounded in the exact
                      metrics shown on this page - never invented figures, never buy/sell advice.
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="peers">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Same sector: {detail?.sector}</CardTitle>
                </CardHeader>
                <CardContent>
                  {peers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No other seeded companies in this sector yet.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {peers.map((peer) => (
                        <Button key={peer.id} asChild variant="outline" size="sm">
                          <Link href={`/stocks/${peer.symbol}`}>
                            {peer.symbol} &middot; {peer.name}
                          </Link>
                        </Button>
                      ))}
                    </div>
                  )}
                  <p className="mt-4 text-xs text-muted-foreground">
                    Full side-by-side peer comparison arrives with the Compare feature in a later
                    phase.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
      <Footer />
    </div>
  );
}
