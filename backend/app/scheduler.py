"""The first background/scheduled job in this codebase. Only runs when
MARKET_DATA_PROVIDER=real - there's nothing to sync under mock data.

Runs once daily on weekdays, after NSE's typical bhavcopy publish window, to
pull that day's real price data and keep price-derived ratios (P/E, market
cap) consistent with it. A holiday just means sync_price_history_for_date
returns 0 - not an error, nothing to alert on.

Known limitation: if this app ever runs with multiple uvicorn worker
processes, each would start its own scheduler and double-sync the same day.
Harmless (upserts are idempotent) but wasteful - not a concern for the
current single-process setup; would need a leader-election guard if that
changes later.
"""

from __future__ import annotations

import logging
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models.company import Company
from app.models.sync_log import SyncSource, SyncStatus
from app.services.market_data_sync import (
    record_sync_result,
    refresh_financial_ratios_from_latest_price,
    sync_price_history_for_date,
)

logger = logging.getLogger("stockai.scheduler")

IST = ZoneInfo("Asia/Kolkata")

_scheduler: AsyncIOScheduler | None = None


def _run_daily_sync() -> None:
    db = SessionLocal()
    trade_date = date.today()
    try:
        rows_synced = sync_price_history_for_date(db, trade_date)
        if rows_synced:
            for company in db.query(Company).all():
                refresh_financial_ratios_from_latest_price(db, company)
        record_sync_result(db, trade_date, SyncSource.scheduled, SyncStatus.success, rows_synced=rows_synced)
        db.commit()
        logger.info("Daily NSE sync for %s: %d rows synced", trade_date, rows_synced)
    except Exception as exc:
        db.rollback()
        logger.exception("Daily NSE sync failed")
        try:
            record_sync_result(db, trade_date, SyncSource.scheduled, SyncStatus.failure, error_message=str(exc))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to record the sync failure itself")
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone=IST)
    _scheduler.add_job(
        _run_daily_sync,
        CronTrigger(day_of_week="mon-fri", hour=20, minute=0, timezone=IST),
        id="daily_nse_sync",
    )
    _scheduler.start()
    logger.info("Started daily NSE sync scheduler (weekdays, 20:00 IST)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
