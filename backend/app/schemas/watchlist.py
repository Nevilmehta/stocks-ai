import uuid
from datetime import datetime

from pydantic import BaseModel


class WatchlistAddRequest(BaseModel):
    symbol: str


class WatchlistItemOut(BaseModel):
    id: uuid.UUID
    symbol: str
    name: str
    sector: str
    added_at: datetime

    latest_price: float | None
    change_percent: float | None
    ai_score: int | None
    ai_label: str | None
    pe_ratio: float | None
    roe: float | None
