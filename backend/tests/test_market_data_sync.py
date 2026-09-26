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
