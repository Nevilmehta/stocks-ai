import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.financials import PeriodType


class StockDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    description: str
    index_memberships: list[str] = []

    latest_price: float | None
    previous_close: float | None
    change: float | None
    change_percent: float | None
    as_of: datetime.date | None

    market_cap: float | None
    pe_ratio: float | None
    pb_ratio: float | None
    roe: float | None
    roce: float | None
    eps: float | None
    debt_to_equity: float | None
    revenue_growth: float | None
    profit_growth: float | None
    week52_high: float | None
    week52_low: float | None
    volume: int | None = None


class PricePoint(BaseModel):
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: int


class IntradayPoint(BaseModel):
    time: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class IntradayHistory(BaseModel):
    trading_date: datetime.date | None
    points: list[IntradayPoint]


class FinancialPeriod(BaseModel):
    period_type: PeriodType
    period_label: str
    fiscal_year: int

    revenue: float
    net_profit: float
    operating_profit: float
    eps: float
    operating_cash_flow: float
    total_debt: float

    pe_ratio: float | None = None
    pb_ratio: float | None = None
    roe: float | None = None
    roce: float | None = None
    debt_to_equity: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    net_margin: float | None = None
    market_cap: float | None = None


class TechnicalIndicators(BaseModel):
    as_of: datetime.date | None

    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    rsi_14: float | None

    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None

    bollinger_upper: float | None
    bollinger_middle: float | None
    bollinger_lower: float | None

    week52_high: float | None
    week52_low: float | None

    return_1m: float | None
    return_3m: float | None
    return_6m: float | None
    return_1y: float | None
    volatility: float | None

    price_vs_sma50_percent: float | None
    price_vs_sma200_percent: float | None
    price_vs_ema50_percent: float | None = None
    price_vs_ema200_percent: float | None = None

    trend: str
    momentum: str

    swing_structure: str = "Not computed"
    fibonacci_levels: dict[str, float] | None = None
    nearest_fibonacci_level: str | None = None
    nearest_fibonacci_distance_percent: float | None = None

    signal: str = "neutral"
    signal_reasons: list[str] = []
    historical_oversold_forward_return: dict | None = None


class SectorCount(BaseModel):
    sector: str
    count: int


class MoverStock(BaseModel):
    symbol: str
    name: str
    sector: str
    latest_price: float
    change_percent: float


class MarketOverview(BaseModel):
    total_companies: int
    sectors: int
    sector_breakdown: list[SectorCount]
    advancers: int
    decliners: int
    unchanged: int
    top_gainers: list[MoverStock]
    top_losers: list[MoverStock]


class AIScoreSubscores(BaseModel):
    financial_strength: float
    growth: float
    profitability: float
    valuation: float
    technical_momentum: float
    risk: float  # 0-100 "safety" score - higher means lower risk


class AIScore(BaseModel):
    symbol: str
    as_of: datetime.date | None
    overall_score: int
    label: str
    risk_label: str
    subscores: AIScoreSubscores
    methodology_note: str
