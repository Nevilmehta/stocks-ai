export type UserRole = "user" | "admin";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  index_memberships: string[];
}

export interface HealthStatus {
  status: string;
  app_env: string;
  market_data_provider: "mock" | "real";
  ai_provider: "mock" | "gemini" | "groq" | "custom";
  last_market_sync: string | null;
  last_sync_check_at: string | null;
}

export type TimeRange = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "3Y" | "MAX";

export interface StockDetail {
  id: string;
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  description: string;
  index_memberships: string[];

  latest_price: number | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  as_of: string | null;

  market_cap: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  roce: number | null;
  eps: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  profit_growth: number | null;
  week52_high: number | null;
  week52_low: number | null;
  volume: number | null;
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IntradayPoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IntradayHistory {
  trading_date: string | null;
  points: IntradayPoint[];
}

export type PeriodType = "annual" | "quarterly";

export interface FinancialPeriod {
  period_type: PeriodType;
  period_label: string;
  fiscal_year: number;

  revenue: number;
  net_profit: number;
  operating_profit: number;
  eps: number;
  operating_cash_flow: number;
  total_debt: number;

  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  roce: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  profit_growth: number | null;
  net_margin: number | null;
  market_cap: number | null;
}

export interface TechnicalIndicators {
  as_of: string | null;

  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  ema_20: number | null;
  ema_50: number | null;
  ema_200: number | null;
  rsi_14: number | null;

  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;

  bollinger_upper: number | null;
  bollinger_middle: number | null;
  bollinger_lower: number | null;

  week52_high: number | null;
  week52_low: number | null;

  return_1m: number | null;
  return_3m: number | null;
  return_6m: number | null;
  return_1y: number | null;
  volatility: number | null;

  price_vs_sma50_percent: number | null;
  price_vs_sma200_percent: number | null;
  price_vs_ema50_percent: number | null;
  price_vs_ema200_percent: number | null;

  trend: string;
  momentum: string;

  swing_structure: string;
  fibonacci_levels: Record<string, number> | null;
  nearest_fibonacci_level: string | null;
  nearest_fibonacci_distance_percent: number | null;

  signal: TradeSignal;
  signal_reasons: string[];
  historical_oversold_forward_return: { occurrences: number; avg_forward_return_30d: number } | null;
}

export type TradeSignal = "buy" | "sell" | "neutral";

export interface SectorCount {
  sector: string;
  count: number;
}

export interface MoverStock {
  symbol: string;
  name: string;
  sector: string;
  latest_price: number;
  change_percent: number;
}

export interface MarketOverview {
  total_companies: number;
  sectors: number;
  sector_breakdown: SectorCount[];
  advancers: number;
  decliners: number;
  unchanged: number;
  top_gainers: MoverStock[];
  top_losers: MoverStock[];
}

export interface AIScoreSubscores {
  financial_strength: number;
  growth: number;
  profitability: number;
  valuation: number;
  technical_momentum: number;
  risk: number;
}

export interface AIScore {
  symbol: string;
  as_of: string | null;
  overall_score: number;
  label: string;
  risk_label: string;
  subscores: AIScoreSubscores;
  methodology_note: string;
}

export interface AIAnalysis {
  symbol: string;
  generated_at: string;
  provider: string;
  summary: string;
  financial_health: string;
  growth: string;
  profitability: string;
  valuation: string;
  technical_picture: string;
  strengths: string[];
  risks: string[];
  things_to_monitor: string[];
  conclusion: string;
  disclaimer: string;
}

export type MessageRole = "user" | "assistant";

export interface ResearchMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ResearchSession {
  id: string;
  title: string;
  created_at: string;
  messages: ResearchMessage[];
}

export interface ResearchSessionSummary {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
  last_message_preview: string | null;
}

export interface WatchlistItem {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  added_at: string;
  latest_price: number | null;
  change_percent: number | null;
  ai_score: number | null;
  ai_label: string | null;
  pe_ratio: number | null;
  roe: number | null;
}

export interface CompareRow {
  symbol: string;
  name: string;
  sector: string;
  latest_price: number | null;
  change_percent: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  roce: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  profit_growth: number | null;
  ai_score: number | null;
  ai_label: string | null;
  technical_momentum: number | null;
  risk_label: string | null;
  history: PricePoint[];
}

export interface CompareResponse {
  rows: CompareRow[];
}

export interface ScreenerRow {
  symbol: string;
  name: string;
  sector: string;
  latest_price: number | null;
  change_percent: number | null;
  volume: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  roe: number | null;
  roce: number | null;
  debt_to_equity: number | null;
  revenue_growth: number | null;
  profit_growth: number | null;
  ai_score: number | null;
  ai_label: string | null;
}

export interface ScreenerFilters {
  sector?: string;
  market_cap_min?: number;
  pe_max?: number;
  roe_min?: number;
  roce_min?: number;
  debt_to_equity_max?: number;
  revenue_growth_min?: number;
  profit_growth_min?: number;
  ai_score_min?: number;
}

export type IndicatorKey = "overall" | "sma" | "ema" | "rsi" | "macd" | "bollinger" | "fibonacci";

export interface SmartIndicatorRow {
  symbol: string;
  name: string;
  sector: string;

  latest_price: number | null;
  change_percent: number | null;
  volume: number | null;
  return_1d: number | null;
  return_1w: number | null;
  return_1m: number | null;
  pe_ratio: number | null;

  rsi_14: number | null;
  trend: string;
  swing_structure: string;
  nearest_fibonacci_level: string | null;

  signal: TradeSignal;
  signal_reasons: string[];

  indicator: IndicatorKey;
  indicator_label: string;
  indicator_value: number | null;
}

export interface SmartIndicatorFilters {
  sector?: string;
  indicator?: IndicatorKey;
  signal?: TradeSignal;
  rsi_state?: "oversold" | "overbought" | "any";
  trend_structure?: "uptrend" | "downtrend" | "sideways" | "any";
}

export interface IndicatorOption {
  key: IndicatorKey;
  label: string;
}

export interface SmartIndicatorMeta {
  available_indicators: IndicatorOption[];
  default_indicator: IndicatorKey;
}

export interface MostResearchedStock {
  symbol: string;
  name: string;
  mention_count: number;
}

export interface AdminAnalytics {
  total_users: number;
  active_users: number;
  total_research_sessions: number;
  total_research_messages: number;
  most_researched: MostResearchedStock[];
}

export type SyncSource = "scheduled" | "manual_admin" | "manual_upload" | "catch_up";
export type SyncStatus = "success" | "failure";

export interface SyncLogEntry {
  trade_date: string;
  source: SyncSource;
  status: SyncStatus;
  rows_synced: number;
  error_message: string | null;
  created_at: string;
}

export interface SyncHistoryResponse {
  last_sync: SyncLogEntry | null;
  history: SyncLogEntry[];
}

export interface UploadFileResult {
  filename: string;
  trade_date: string | null;
  rows_synced: number;
  error: string | null;
}

export interface MarketDataUploadResponse {
  results: UploadFileResult[];
}

export interface StrategyConfig {
  enable_sma: boolean;
  enable_ema: boolean;
  enable_rsi: boolean;
  enable_macd: boolean;
  enable_bollinger: boolean;
  enable_fibonacci: boolean;
  default_smart_indicator: IndicatorKey;

  sma_short: number;
  sma_medium: number;
  sma_long: number;
  ema_short: number;
  ema_medium: number;
  ema_long: number;
  rsi_period: number;
  macd_fast: number;
  macd_slow: number;
  macd_signal: number;
  bollinger_period: number;
  bollinger_num_std: number;
  fibonacci_lookback_days: number;

  weight_financial_strength: number;
  weight_growth: number;
  weight_profitability: number;
  weight_valuation: number;
  weight_technical_momentum: number;
  weight_risk: number;

  debt_to_equity_good: number;
  debt_to_equity_bad: number;
  roe_low: number;
  roe_high: number;
  roce_low: number;
  roce_high: number;
  pe_fallback_low: number;
  pe_fallback_high: number;
  rsi_oversold: number;
  rsi_overbought: number;
  risk_low_cutoff: number;
  risk_moderate_cutoff: number;
  overall_very_strong_cutoff: number;
  overall_strong_cutoff: number;
  overall_balanced_cutoff: number;
  overall_weak_cutoff: number;
}

export interface StrategyOut {
  id: string;
  name: string;
  description: string;
  config: StrategyConfig;
  is_active: boolean;
  created_at: string;
}

export interface StrategyPreviewRow {
  symbol: string;
  name: string;
  active_score: number | null;
  active_label: string | null;
  proposed_score: number | null;
  proposed_label: string | null;
  delta: number | null;
}

export interface StrategyPreviewResponse {
  active_strategy_name: string;
  results: StrategyPreviewRow[];
}

export interface BacktestCheckpoint {
  symbol: string;
  checkpoint_date: string;
  active_score: number | null;
  proposed_score: number | null;
  forward_return_30d: number | null;
  forward_return_90d: number | null;
}

export interface StrategyBacktestResponse {
  active_strategy_name: string;
  checkpoints: BacktestCheckpoint[];
  caveat: string;
}

export interface AdminNote {
  id: string;
  message: string;
  is_active: boolean;
  created_at: string;
}
