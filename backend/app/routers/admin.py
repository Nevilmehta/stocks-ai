import logging
import uuid
from collections import Counter
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import ActiveStrategy, get_active_strategy, get_market_data_provider, require_admin
from app.models.admin_note import AdminNote
from app.models.company import Company
from app.models.research import MessageRole, ResearchMessage, ResearchSession
from app.models.strategy import ResearchStrategy
from app.models.sync_log import MarketDataSyncLog, SyncSource, SyncStatus
from app.models.user import User
from app.providers.market_data import MarketDataProvider
from app.schemas.admin import (
    AdminAnalytics,
    MarketDataSyncRequest,
    MarketDataSyncResponse,
    MarketDataUploadResponse,
    MostResearchedStock,
    SyncHistoryResponse,
    SyncLogEntry,
    UploadFileResult,
)
from app.schemas.admin_note import AdminNoteCreateRequest, AdminNoteOut
from app.schemas.strategy import (
    DEFAULT_STRATEGY_CONFIG,
    StrategyBacktestRequest,
    StrategyBacktestResponse,
    StrategyConfig,
    StrategyCreateRequest,
    StrategyOut,
    StrategyPreviewRequest,
    StrategyPreviewResponse,
    StrategyUpdateRequest,
)
from app.schemas.user import UserCreate, UserPublic, UserUpdate
from app.security import hash_password
from app.services.company_matching import find_mentioned_companies
from app.services.email_service import send_welcome_email
from app.services.market_data_sync import (
    import_uploaded_bhavcopy,
    record_sync_result,
    refresh_financial_ratios_from_latest_price,
    sync_price_history_for_date,
)
from app.services.nse_bhavcopy import infer_trade_date_from_filename
from app.services.strategy_evaluation import BACKTEST_CAVEAT, run_backtest, run_preview

logger = logging.getLogger("stockai.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_welcome_email, user.display_name, user.email)

    return user


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/market-data/sync", response_model=MarketDataSyncResponse)
def sync_market_data(
    payload: MarketDataSyncRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MarketDataSyncResponse:
    """Manual fallback for a specific day (e.g. if the automatic scheduled sync,
    see app/scheduler.py, ever misses one) - not the primary sync mechanism."""
    settings = get_settings()
    if settings.market_data_provider != "real":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MARKET_DATA_PROVIDER must be 'real' to sync live NSE data.",
        )

    trade_date = payload.trade_date or date.today()
    try:
        rows_synced = sync_price_history_for_date(db, trade_date)
        if rows_synced:
            for company in db.query(Company).all():
                refresh_financial_ratios_from_latest_price(db, company)
        record_sync_result(
            db, trade_date, SyncSource.manual_admin, SyncStatus.success, rows_synced=rows_synced, triggered_by=admin.id
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        record_sync_result(
            db, trade_date, SyncSource.manual_admin, SyncStatus.failure, error_message=str(exc), triggered_by=admin.id
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Sync failed: {exc}") from exc

    return MarketDataSyncResponse(trade_date=trade_date, rows_synced=rows_synced)


@router.post("/market-data/upload", response_model=MarketDataUploadResponse)
def upload_market_data(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> MarketDataUploadResponse:
    """Manual fallback when the automatic/network fetch can't reach NSE at
    all (e.g. after deployment, if the host's IP gets blocked). An admin
    downloads the official bhavcopy ZIP from nseindia.com/all-reports and
    uploads it here - reuses the exact same parser and upsert path as the
    automatic sync (see app/services/market_data_sync.py). Supports multiple
    files in one request for backfilling several missing trading days at
    once; each file is independent, so one bad file doesn't fail the rest."""
    results: list[UploadFileResult] = []
    affected_companies: set = set()

    for upload in files:
        trade_date = infer_trade_date_from_filename(upload.filename or "")
        try:
            if trade_date is None:
                raise ValueError(
                    "Could not determine the trading day from the filename - "
                    "re-upload the file with its original NSE filename intact."
                )
            zip_bytes = upload.file.read()
            rows_synced = import_uploaded_bhavcopy(db, trade_date, zip_bytes)
            record_sync_result(
                db, trade_date, SyncSource.manual_upload, SyncStatus.success, rows_synced=rows_synced, triggered_by=admin.id
            )
            db.commit()
            results.append(
                UploadFileResult(filename=upload.filename or "", trade_date=trade_date, rows_synced=rows_synced, error=None)
            )
            if rows_synced:
                affected_companies.update(c.id for c in db.query(Company).all())
        except Exception as exc:
            db.rollback()
            logger.exception("Failed to import uploaded bhavcopy file %s", upload.filename)
            if trade_date is not None:
                record_sync_result(
                    db, trade_date, SyncSource.manual_upload, SyncStatus.failure, error_message=str(exc), triggered_by=admin.id
                )
                db.commit()
            results.append(
                UploadFileResult(filename=upload.filename or "", trade_date=trade_date, rows_synced=0, error=str(exc))
            )

    if affected_companies:
        for company in db.query(Company).filter(Company.id.in_(affected_companies)).all():
            refresh_financial_ratios_from_latest_price(db, company)
        db.commit()

    return MarketDataUploadResponse(results=results)


@router.get("/market-data/sync-history", response_model=SyncHistoryResponse)
def market_data_sync_history(db: Session = Depends(get_db)) -> SyncHistoryResponse:
    entries = (
        db.query(MarketDataSyncLog)
        .order_by(MarketDataSyncLog.created_at.desc())
        .limit(20)
        .all()
    )
    history = [SyncLogEntry.model_validate(e) for e in entries]
    return SyncHistoryResponse(last_sync=history[0] if history else None, history=history)


@router.get("/analytics", response_model=AdminAnalytics)
def get_analytics(db: Session = Depends(get_db)) -> AdminAnalytics:
    """Platform-wide usage stats. "Most researched" is derived by scanning
    user chat/analyse prompts for company mentions - there's no separate
    tracking table, keeping the schema small (see section 5 of the spec)."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    total_sessions = db.query(ResearchSession).count()
    total_messages = db.query(ResearchMessage).count()

    companies = db.query(Company).all()
    user_messages = db.query(ResearchMessage).filter(ResearchMessage.role == MessageRole.user).all()

    mention_counts: Counter[str] = Counter()
    for message in user_messages:
        for company in find_mentioned_companies(message.content, companies, limit=len(companies)):
            mention_counts[company.symbol] += 1

    companies_by_symbol = {c.symbol: c for c in companies}
    most_researched = [
        MostResearchedStock(symbol=symbol, name=companies_by_symbol[symbol].name, mention_count=count)
        for symbol, count in mention_counts.most_common(5)
    ]

    return AdminAnalytics(
        total_users=total_users,
        active_users=active_users,
        total_research_sessions=total_sessions,
        total_research_messages=total_messages,
        most_researched=most_researched,
    )


@router.get("/strategies", response_model=list[StrategyOut])
def list_strategies(db: Session = Depends(get_db)) -> list[ResearchStrategy]:
    return db.query(ResearchStrategy).order_by(ResearchStrategy.created_at.desc()).all()


@router.get("/strategies/default-config", response_model=StrategyConfig)
def get_default_strategy_config() -> StrategyConfig:
    """Prefills a "create new strategy" form with today's defaults."""
    return DEFAULT_STRATEGY_CONFIG


@router.post("/strategies", response_model=StrategyOut, status_code=status.HTTP_201_CREATED)
def create_strategy(
    payload: StrategyCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ResearchStrategy:
    strategy = ResearchStrategy(
        name=payload.name,
        description=payload.description,
        config=payload.config.model_dump(),
        is_active=False,
        created_by=admin.id,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def _parse_strategy_id(strategy_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(strategy_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid strategy id") from None


@router.patch("/strategies/{strategy_id}", response_model=StrategyOut)
def update_strategy(strategy_id: str, payload: StrategyUpdateRequest, db: Session = Depends(get_db)) -> ResearchStrategy:
    strategy = db.get(ResearchStrategy, _parse_strategy_id(strategy_id))
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    if payload.name is not None:
        strategy.name = payload.name
    if payload.description is not None:
        strategy.description = payload.description
    if payload.config is not None:
        strategy.config = payload.config.model_dump()

    db.commit()
    db.refresh(strategy)
    return strategy


@router.post("/strategies/{strategy_id}/activate", response_model=StrategyOut)
def activate_strategy(strategy_id: str, db: Session = Depends(get_db)) -> ResearchStrategy:
    """Restoring a previous configuration is just activating its (never-deleted)
    row again - deactivates every other row in the same transaction so exactly
    one strategy is ever active."""
    strategy = db.get(ResearchStrategy, _parse_strategy_id(strategy_id))
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    db.query(ResearchStrategy).filter(ResearchStrategy.id != strategy.id).update({"is_active": False})
    strategy.is_active = True
    db.commit()
    db.refresh(strategy)
    return strategy


@router.post("/strategies/preview", response_model=StrategyPreviewResponse)
def preview_strategy(
    payload: StrategyPreviewRequest,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> StrategyPreviewResponse:
    """Read-only: recomputes every tracked company's AI score under the
    candidate config vs the currently-active one, using today's data. Nothing
    is persisted."""
    results = run_preview(provider, active, payload.config)
    return StrategyPreviewResponse(active_strategy_name=active.name, results=results)


@router.post("/strategies/backtest", response_model=StrategyBacktestResponse)
def backtest_strategy(
    payload: StrategyBacktestRequest,
    db: Session = Depends(get_db),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> StrategyBacktestResponse:
    """Basic backtest - see BACKTEST_CAVEAT (also returned in the response)
    for what this does and doesn't account for."""
    checkpoints = run_backtest(db, provider, active, payload.config, payload.symbols)
    return StrategyBacktestResponse(active_strategy_name=active.name, checkpoints=checkpoints, caveat=BACKTEST_CAVEAT)


@router.post("/dashboard-note", response_model=AdminNoteOut, status_code=status.HTTP_201_CREATED)
def post_dashboard_note(
    payload: AdminNoteCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdminNote:
    """Posts a new note, deactivating whichever one is currently shown on the
    customer Dashboard (same deactivate-all-others-in-one-transaction pattern
    as activate_strategy). An empty message IS the "clear the note" action -
    GET /api/dashboard-note already treats an empty/missing active note the
    same way, so no separate clear/delete endpoint is needed."""
    db.query(AdminNote).filter(AdminNote.is_active.is_(True)).update({"is_active": False})
    note = AdminNote(message=payload.message.strip(), is_active=True, created_by=admin.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/dashboard-note/history", response_model=list[AdminNoteOut])
def dashboard_note_history(db: Session = Depends(get_db)) -> list[AdminNote]:
    return db.query(AdminNote).order_by(AdminNote.created_at.desc()).limit(20).all()
