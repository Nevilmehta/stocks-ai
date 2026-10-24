from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.price_history import PriceHistory
from app.models.sync_log import MarketDataSyncLog

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    last_market_sync = db.query(func.max(PriceHistory.date)).scalar()

    # Distinct from last_market_sync: that's the latest date we actually have
    # priced data for (correctly doesn't advance on a holiday, since there's
    # nothing to sync). This is the last time the system actually attempted a
    # check at all, success or not, 0 rows or not - so a holiday still shows
    # "checked today" rather than looking stale just because prices didn't
    # change. See app/scheduler.py's daily job + startup catch-up.
    last_check = (
        db.query(MarketDataSyncLog.created_at)
        .order_by(MarketDataSyncLog.created_at.desc())
        .first()
    )

    return {
        "status": "ok",
        "app_env": settings.app_env,
        "market_data_provider": settings.market_data_provider,
        "ai_provider": settings.ai_provider,
        "last_market_sync": last_market_sync,
        "last_sync_check_at": last_check[0] if last_check else None,
    }
