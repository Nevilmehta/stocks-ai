from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MarketDataSyncRequest(BaseModel):
    trade_date: date | None = None


class MarketDataSyncResponse(BaseModel):
    trade_date: date
    rows_synced: int


class UploadFileResult(BaseModel):
    filename: str
    trade_date: date | None
    rows_synced: int
    error: str | None


class MarketDataUploadResponse(BaseModel):
    results: list[UploadFileResult]


class SyncLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    source: str
    status: str
    rows_synced: int
    error_message: str | None
    created_at: datetime


class SyncHistoryResponse(BaseModel):
    last_sync: SyncLogEntry | None
    history: list[SyncLogEntry]


class MostResearchedStock(BaseModel):
    symbol: str
    name: str
    mention_count: int


class AdminAnalytics(BaseModel):
    total_users: int
    active_users: int
    total_research_sessions: int
    total_research_messages: int
    most_researched: list[MostResearchedStock]
