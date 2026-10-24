from pydantic import BaseModel


class ScreenerRow(BaseModel):
    symbol: str
    name: str
    sector: str

    latest_price: float | None
    change_percent: float | None
    volume: int | None = None
    market_cap: float | None
    pe_ratio: float | None
    roe: float | None
    roce: float | None
    debt_to_equity: float | None
    revenue_growth: float | None
    profit_growth: float | None
    ai_score: int | None
    ai_label: str | None
