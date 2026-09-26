import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.research import MessageRole


class AIAnalysis(BaseModel):
    symbol: str
    generated_at: datetime
    provider: str

    summary: str
    financial_health: str
    growth: str
    profitability: str
    valuation: str
    technical_picture: str
    strengths: list[str]
    risks: list[str]
    things_to_monitor: list[str]
    conclusion: str
    disclaimer: str


class AnalyseRequest(BaseModel):
    symbol: str


class ChatRequest(BaseModel):
    message: str
    session_id: uuid.UUID | None = None


class ResearchMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ResearchSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    messages: list[ResearchMessageOut]


class ResearchSessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    message_count: int
    last_message_preview: str | None
