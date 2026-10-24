from datetime import date

from app import scheduler
from app.models.sync_log import MarketDataSyncLog, SyncSource, SyncStatus


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


def test_run_catch_up_records_a_log_entry_when_days_were_synced(db_session, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        scheduler,
        "backfill_missing_trading_days",
        lambda db, up_to: {"days_synced": 2, "rows_synced": 40, "latest_date": date(2024, 1, 2)},
    )
    monkeypatch.setattr(db_session, "close", lambda: None)

    scheduler._run_catch_up()

    entry = db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.source == SyncSource.catch_up).first()
    assert entry is not None
    assert entry.status == SyncStatus.success
    assert entry.rows_synced == 40


def test_run_catch_up_logs_nothing_when_already_current(db_session, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        scheduler,
        "backfill_missing_trading_days",
        lambda db, up_to: {"days_synced": 0, "rows_synced": 0, "latest_date": date.today()},
    )
    monkeypatch.setattr(db_session, "close", lambda: None)

    scheduler._run_catch_up()

    assert db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.source == SyncSource.catch_up).count() == 0


def test_run_catch_up_handles_failure_without_raising(db_session, monkeypatch):
    def _boom(db, up_to):
        raise RuntimeError("DB unreachable")

    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(scheduler, "backfill_missing_trading_days", _boom)
    monkeypatch.setattr(db_session, "close", lambda: None)

    scheduler._run_catch_up()  # must not raise

    assert db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.source == SyncSource.catch_up).count() == 0
