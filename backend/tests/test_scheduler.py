from datetime import date

from app import scheduler
from app.models.sync_log import MarketDataSyncLog, SyncStatus


def test_run_daily_sync_records_success(db_session, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(scheduler, "sync_price_history_for_date", lambda db, trade_date: 5)
    monkeypatch.setattr(scheduler, "refresh_financial_ratios_from_latest_price", lambda db, company: None)
    monkeypatch.setattr(db_session, "close", lambda: None)

    scheduler._run_daily_sync()

    entry = db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.trade_date == date.today()).first()
    assert entry is not None
    assert entry.status == SyncStatus.success
    assert entry.rows_synced == 5


def test_run_daily_sync_records_failure(db_session, monkeypatch):
    def _boom(db, trade_date):
        raise RuntimeError("NSE unreachable")

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(scheduler, "sync_price_history_for_date", _boom)
    monkeypatch.setattr(db_session, "close", lambda: None)

    scheduler._run_daily_sync()

    entry = db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.trade_date == date.today()).first()
    assert entry is not None
    assert entry.status == SyncStatus.failure
    assert "NSE unreachable" in entry.error_message
