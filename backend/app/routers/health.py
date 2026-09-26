from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.price_history import PriceHistory

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    last_market_sync = db.query(func.max(PriceHistory.date)).scalar()
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "market_data_provider": settings.market_data_provider,
        "ai_provider": settings.ai_provider,
        "last_market_sync": last_market_sync,
    }
