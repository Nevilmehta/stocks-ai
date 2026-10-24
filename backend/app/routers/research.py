import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import ActiveStrategy, get_active_strategy, get_ai_provider, get_current_user, get_market_data_provider
from app.models.research import MessageRole, ResearchMessage, ResearchSession
from app.models.user import User
from app.providers.ai_provider import AIProvider
from app.providers.market_data import MarketDataProvider
from app.services.company_matching import find_mentioned_companies
from app.services.historical_price_lookup import (
    available_date_range,
    extract_date_from_message,
    is_price_lookup_question,
    lookup_historical_price,
)
from app.services.stock_context import build_market_overview_context, build_stock_context
from app.schemas.research import (
    AIAnalysis,
    AnalyseRequest,
    ChatRequest,
    ResearchSessionOut,
    ResearchSessionSummary,
)

router = APIRouter(prefix="/api/research", tags=["research"], dependencies=[Depends(get_current_user)])

# Heuristic for routing a no-company-mentioned question to the market-overview
# answerer instead of the generic "mention a company" fallback - covers both
# "top stocks today" style questions and "when was this updated" style ones,
# since both are really "tell me about the general data state" questions.
_MARKET_WIDE_KEYWORDS = (
    "top stock", "top 5", "top5", "top gainer", "top loser", "gainers", "losers", "movers",
    "market today", "today's market", "whole market", "best performing", "worst performing",
    "last updated", "when updated", "how fresh", "latest data", "data updated", "when was",
    "last sync", "up to date", "how current",
)


def _is_market_wide_question(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _MARKET_WIDE_KEYWORDS)


def _render_analysis_as_text(analysis: AIAnalysis) -> str:
    lines = [
        analysis.summary,
        "",
        f"Financial Health: {analysis.financial_health}",
        f"Growth: {analysis.growth}",
        f"Profitability: {analysis.profitability}",
        f"Valuation: {analysis.valuation}",
        f"Technical Picture: {analysis.technical_picture}",
        "",
        "Strengths:",
        *[f"- {item}" for item in analysis.strengths],
        "",
        "Risks:",
        *[f"- {item}" for item in analysis.risks],
        "",
        "Things to monitor:",
        *[f"- {item}" for item in analysis.things_to_monitor],
        "",
        analysis.conclusion,
        "",
        analysis.disclaimer,
    ]
    return "\n".join(lines)


def _attach_messages(db: Session, session: ResearchSession) -> ResearchSession:
    session.messages = (
        db.query(ResearchMessage)
        .filter(ResearchMessage.session_id == session.id)
        .order_by(ResearchMessage.created_at.asc())
        .all()
    )
    return session


def _add_message_pair(db: Session, session_id: uuid.UUID, user_message: str, assistant_message: str) -> None:
    # Explicit, staggered timestamps guarantee correct ordering even when the
    # underlying DB's timestamp precision would otherwise tie a user/assistant
    # pair written in the same transaction.
    now = datetime.now(timezone.utc)
    db.add(ResearchMessage(session_id=session_id, role=MessageRole.user, content=user_message, created_at=now))
    db.add(
        ResearchMessage(
            session_id=session_id,
            role=MessageRole.assistant,
            content=assistant_message,
            created_at=now + timedelta(microseconds=1000),
        )
    )


def _save_exchange(db: Session, user: User, title: str, user_message: str, assistant_message: str) -> ResearchSession:
    session = ResearchSession(user_id=user.id, title=title[:200])
    db.add(session)
    db.flush()
    _add_message_pair(db, session.id, user_message, assistant_message)
    db.commit()
    db.refresh(session)
    return _attach_messages(db, session)


@router.post("/analyse", response_model=AIAnalysis)
def analyse_stock(
    payload: AnalyseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    ai_provider: AIProvider = Depends(get_ai_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> AIAnalysis:
    context = build_stock_context(payload.symbol, provider, active)
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    analysis = ai_provider.analyse_stock(context)

    _save_exchange(
        db,
        user,
        title=f"Analyse {context.detail.symbol}",
        user_message=f"Analyse {context.detail.symbol}",
        assistant_message=_render_analysis_as_text(analysis),
    )

    return analysis


@router.post("/chat", response_model=ResearchSessionOut)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    ai_provider: AIProvider = Depends(get_ai_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> ResearchSession:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    all_companies = provider.search_stocks("", limit=5000)
    mentioned = find_mentioned_companies(message, all_companies)
    contexts = [ctx for c in mentioned if (ctx := build_stock_context(c.symbol, provider, active)) is not None]

    requested_date = (
        extract_date_from_message(message, date.today()) if len(contexts) == 1 and is_price_lookup_question(message) else None
    )

    if len(contexts) >= 2:
        answer = ai_provider.compare_stocks(contexts)
    elif requested_date is not None:
        symbol = contexts[0].detail.symbol
        name = contexts[0].detail.name
        historical = lookup_historical_price(provider, symbol, name, requested_date)
        if historical is not None:
            answer = ai_provider.answer_historical_price_question(message, historical)
        else:
            date_range = available_date_range(provider, symbol)
            if date_range:
                answer = (
                    f"No price data for {name} ({symbol}) on {requested_date.isoformat()} - "
                    f"this app's price history covers {date_range[0].isoformat()} to "
                    f"{date_range[1].isoformat()}. Try a date within that range."
                )
            else:
                answer = f"No price history is available for {name} ({symbol}) at all yet."
    elif not contexts and _is_market_wide_question(message):
        overview = build_market_overview_context(provider, active)
        answer = ai_provider.answer_market_question(message, overview)
    else:
        answer = ai_provider.answer_question(message, contexts)

    if payload.session_id is not None:
        session = (
            db.query(ResearchSession)
            .filter(ResearchSession.id == payload.session_id, ResearchSession.user_id == user.id)
            .first()
        )
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")
        _add_message_pair(db, session.id, message, answer)
        db.commit()
        db.refresh(session)
        return _attach_messages(db, session)

    return _save_exchange(db, user, title=message, user_message=message, assistant_message=answer)


@router.get("/history", response_model=list[ResearchSessionSummary])
def research_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ResearchSessionSummary]:
    sessions = (
        db.query(ResearchSession)
        .filter(ResearchSession.user_id == user.id)
        .order_by(ResearchSession.created_at.desc())
        .all()
    )

    summaries: list[ResearchSessionSummary] = []
    for session in sessions:
        message_count = (
            db.query(ResearchMessage).filter(ResearchMessage.session_id == session.id).count()
        )
        # Prefer the latest assistant reply for the preview (more useful than
        # echoing the user's own question) - explicit role filter avoids relying
        # on created_at ordering, which can tie when a user/assistant pair is
        # written in the same transaction.
        last_assistant = (
            db.query(ResearchMessage)
            .filter(ResearchMessage.session_id == session.id, ResearchMessage.role == MessageRole.assistant)
            .order_by(ResearchMessage.created_at.desc())
            .first()
        )
        summaries.append(
            ResearchSessionSummary(
                id=session.id,
                title=session.title,
                created_at=session.created_at,
                message_count=message_count,
                last_message_preview=(last_assistant.content[:160] if last_assistant else None),
            )
        )
    return summaries


@router.get("/history/{session_id}", response_model=ResearchSessionOut)
def research_session_detail(
    session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ResearchSession:
    session = (
        db.query(ResearchSession)
        .filter(ResearchSession.id == session_id, ResearchSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")

    return _attach_messages(db, session)
