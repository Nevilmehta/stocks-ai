from pydantic import BaseModel

from app.schemas.stock import PricePoint


class CompareRow(BaseModel):
    symbol: str
    name: str
    sector: str

    latest_price: float | None
    change_percent: float | None
    market_cap: float | None
    pe_ratio: float | None
    pb_ratio: float | None
    roe: float | None
    roce: float | None
    debt_to_equity: float | None
    revenue_growth: float | None
    profit_growth: float | None

    ai_score: int | None
    ai_label: str | None
    technical_momentum: float | None
    risk_label: str | None

    history: list[PricePoint]


class CompareResponse(BaseModel):
    rows: list[CompareRow]


class CompareRequest(BaseModel):
    symbols: list[str]


class CompareAIResponse(BaseModel):
    text: str
