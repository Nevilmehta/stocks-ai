from datetime import date

from app.models.company import Company
from app.models.financials import FinancialRatios
from app.models.price_history import PriceHistory
from app.services import market_data_sync
from app.services.nse_bhavcopy import BhavcopyRow


def _create_company(db_session, symbol="TCS") -> Company:
    company = Company(
        symbol=symbol,
        name="Tata Consultancy Services",
        sector="Information Technology",
        industry="IT Services",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_sync_price_history_returns_zero_on_non_trading_day(db_session, monkeypatch):
    _create_company(db_session)
    monkeypatch.setattr(market_data_sync, "fetch_bhavcopy", lambda trade_date: None)

    rows_synced = market_data_sync.sync_price_history_for_date(db_session, date(2024, 1, 6))

    assert rows_synced == 0


def test_sync_price_history_inserts_then_updates(db_session, monkeypatch):
    company = _create_company(db_session)
    trade_date = date(2024, 1, 2)

    monkeypatch.setattr(
        market_data_sync,
        "fetch_bhavcopy",
        lambda trade_date: [BhavcopyRow(symbol="TCS", open=100, high=110, low=95, close=105, volume=1000)],
    )

    rows_synced = market_data_sync.sync_price_history_for_date(db_session, trade_date)
    db_session.commit()

    assert rows_synced == 1
    rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == company.id).all()
    assert len(rows) == 1
    assert float(rows[0].close) == 105

    monkeypatch.setattr(
        market_data_sync,
        "fetch_bhavcopy",
        lambda trade_date: [BhavcopyRow(symbol="TCS", open=101, high=112, low=96, close=108, volume=1200)],
    )
    rows_synced_again = market_data_sync.sync_price_history_for_date(db_session, trade_date)
    db_session.commit()

    assert rows_synced_again == 1
    rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == company.id).all()
    assert len(rows) == 1, "same date should update in place, not duplicate"
    assert float(rows[0].close) == 108


def test_sync_price_history_bulk_handles_multiple_companies_mixed_insert_update(db_session, monkeypatch):
    tcs = _create_company(db_session, symbol="TCS")
    infy = _create_company(db_session, symbol="INFY")
    trade_date = date(2024, 1, 2)

    # TCS already has a row for this date (should update in place); INFY doesn't (should insert).
    db_session.add(PriceHistory(company_id=tcs.id, date=trade_date, open=1, high=1, low=1, close=1, volume=1))
    db_session.commit()

    monkeypatch.setattr(
        market_data_sync,
        "fetch_bhavcopy",
        lambda trade_date: [
            BhavcopyRow(symbol="TCS", open=100, high=110, low=95, close=105, volume=1000),
            BhavcopyRow(symbol="INFY", open=200, high=210, low=195, close=205, volume=2000),
        ],
    )

    rows_synced = market_data_sync.sync_price_history_for_date(db_session, trade_date)
    db_session.commit()

    assert rows_synced == 2
    tcs_rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == tcs.id).all()
    infy_rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == infy.id).all()
    assert len(tcs_rows) == 1 and float(tcs_rows[0].close) == 105
    assert len(infy_rows) == 1 and float(infy_rows[0].close) == 205


def test_sync_price_history_skips_untracked_symbols(db_session, monkeypatch):
    _create_company(db_session, symbol="TCS")
    monkeypatch.setattr(
        market_data_sync,
        "fetch_bhavcopy",
        lambda trade_date: [BhavcopyRow(symbol="RANDOMCO", open=1, high=1, low=1, close=1, volume=1)],
    )

    rows_synced = market_data_sync.sync_price_history_for_date(db_session, date(2024, 1, 2))

    assert rows_synced == 0


def test_refresh_financial_ratios_uses_latest_close_price(db_session):
    company = _create_company(db_session)
    db_session.add(
        PriceHistory(company_id=company.id, date=date(2024, 1, 2), open=100, high=110, low=95, close=100, volume=1000)
    )
    db_session.add(
        PriceHistory(company_id=company.id, date=date(2024, 1, 3), open=101, high=112, low=96, close=200, volume=1200)
    )
    db_session.commit()

    market_data_sync.refresh_financial_ratios_from_latest_price(db_session, company)
    db_session.commit()

    ratios = db_session.query(FinancialRatios).filter(FinancialRatios.company_id == company.id).all()
    assert len(ratios) > 0
    assert all(float(r.market_cap) > 0 for r in ratios)


def test_refresh_financial_ratios_noop_without_price_history(db_session):
    company = _create_company(db_session)

    market_data_sync.refresh_financial_ratios_from_latest_price(db_session, company)
    db_session.commit()

    ratios = db_session.query(FinancialRatios).filter(FinancialRatios.company_id == company.id).all()
    assert ratios == []


def test_backfill_missing_trading_days_noop_when_already_current(db_session, monkeypatch):
    company = _create_company(db_session)
    db_session.add(
        PriceHistory(company_id=company.id, date=date(2024, 1, 10), open=1, high=1, low=1, close=1, volume=1)
    )
    db_session.commit()

    def _should_not_be_called(trade_date):
        raise AssertionError("fetch_bhavcopy should not run when there is no gap to fill")

    monkeypatch.setattr(market_data_sync, "fetch_bhavcopy", _should_not_be_called)

    result = market_data_sync.backfill_missing_trading_days(db_session, date(2024, 1, 10))

    assert result == {"days_synced": 0, "rows_synced": 0, "latest_date": date(2024, 1, 10)}


def test_backfill_missing_trading_days_fills_the_gap(db_session, monkeypatch):
    company = _create_company(db_session)
    # 2024-01-04 is a Thursday.
    db_session.add(
        PriceHistory(company_id=company.id, date=date(2024, 1, 4), open=1, high=1, low=1, close=1, volume=1)
    )
    db_session.commit()

    # 2024-01-05 (Fri) is a real trading day (returns data); 2024-01-08 (Mon)
    # is a simulated holiday (returns None, 0 rows) - both must be handled,
    # and the 01-06/01-07 weekend in between must be skipped entirely, never
    # even fetched.
    def _fake_fetch(trade_date):
        if trade_date == date(2024, 1, 5):
            return [BhavcopyRow(symbol="TCS", open=10, high=11, low=9, close=10, volume=100)]
        if trade_date == date(2024, 1, 8):
            return None
        raise AssertionError(f"should not fetch a weekend date: {trade_date}")

    monkeypatch.setattr(market_data_sync, "fetch_bhavcopy", _fake_fetch)

    result = market_data_sync.backfill_missing_trading_days(db_session, date(2024, 1, 8))

    assert result["days_synced"] == 1
    assert result["rows_synced"] == 1
    rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == company.id).all()
    assert len(rows) == 2
    new_row = next(r for r in rows if r.date == date(2024, 1, 5))
    assert float(new_row.close) == 10


def test_backfill_missing_trading_days_continues_past_a_failed_day(db_session, monkeypatch):
    company = _create_company(db_session)
    db_session.add(
        PriceHistory(company_id=company.id, date=date(2024, 1, 2), open=1, high=1, low=1, close=1, volume=1)
    )
    db_session.commit()

    def _fake_fetch(trade_date):
        if trade_date == date(2024, 1, 3):
            raise RuntimeError("NSE unreachable")
        return [BhavcopyRow(symbol="TCS", open=10, high=11, low=9, close=10, volume=100)]

    monkeypatch.setattr(market_data_sync, "fetch_bhavcopy", _fake_fetch)

    result = market_data_sync.backfill_missing_trading_days(db_session, date(2024, 1, 4))

    assert result["days_synced"] == 1
    rows = db_session.query(PriceHistory).filter(PriceHistory.company_id == company.id).all()
    assert {r.date for r in rows} == {date(2024, 1, 2), date(2024, 1, 4)}
