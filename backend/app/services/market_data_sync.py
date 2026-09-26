"""Upserts real NSE price history into Postgres, and keeps price-derived
ratios (P/E, market cap) consistent with the real price. Company list and raw
financials (revenue/profit/eps) stay on the existing demo generator - see
app/seed/market_data.py and the module docstring on app/providers/market_data.py
for why.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

import uuid

from app.models.company import Company
from app.models.financials import FinancialRatios
from app.models.price_history import PriceHistory
from app.models.sync_log import MarketDataSyncLog, SyncSource, SyncStatus
from app.seed.market_data import generate_financial_profile, generate_ratios
from app.services.nse_bhavcopy import BhavcopyRow, fetch_bhavcopy, parse_bhavcopy_zip


def upsert_price_history_rows(db: Session, trade_date: date, bhav_rows: list[BhavcopyRow]) -> int:
    """Upserts PriceHistory rows for every tracked Company found in `bhav_rows`
    (keyed on the existing (company_id, date) unique constraint). Shared by
    both the automatic/manual NSE fetch path and the admin file-upload path -
    neither duplicates this logic."""
    bhav_by_symbol = {row.symbol: row for row in bhav_rows}
    companies = db.query(Company).all()

    synced = 0
    for company in companies:
        row = bhav_by_symbol.get(company.symbol)
        if row is None:
            continue

        existing = (
            db.query(PriceHistory)
            .filter(PriceHistory.company_id == company.id, PriceHistory.date == trade_date)
            .first()
        )
        if existing is None:
            existing = PriceHistory(company_id=company.id, date=trade_date)
            db.add(existing)

        existing.open = row.open
        existing.high = row.high
        existing.low = row.low
        existing.close = row.close
        existing.volume = row.volume
        synced += 1

    return synced


def sync_price_history_for_date(db: Session, trade_date: date) -> int:
    """Fetches one day's NSE bhavcopy over the network and upserts it. Returns
    0, not an error, if trade_date wasn't a trading day (weekend/holiday)."""
    bhav_rows = fetch_bhavcopy(trade_date)
    if not bhav_rows:
        return 0
    return upsert_price_history_rows(db, trade_date, bhav_rows)


def import_uploaded_bhavcopy(db: Session, trade_date: date, zip_bytes: bytes) -> int:
    """Parses an admin-uploaded bhavcopy ZIP (the official file downloaded by
    hand from nseindia.com/all-reports) and upserts it - the manual fallback
    for when the automatic/scheduled fetch can't reach NSE itself. Reuses the
    exact same parser and upsert path as the automatic sync."""
    bhav_rows = parse_bhavcopy_zip(trade_date, zip_bytes)
    return upsert_price_history_rows(db, trade_date, bhav_rows)


def record_sync_result(
    db: Session,
    trade_date: date,
    source: SyncSource,
    status: SyncStatus,
    rows_synced: int = 0,
    error_message: str | None = None,
    triggered_by: uuid.UUID | None = None,
) -> None:
    """One row per sync attempt (scheduled, admin-triggered, or upload) - backs
    the admin dashboard's last-sync status, failure warning, and import
    history. Caller is responsible for committing."""
    db.add(
        MarketDataSyncLog(
            trade_date=trade_date,
            source=source,
            status=status,
            rows_synced=rows_synced,
            error_message=error_message,
            triggered_by=triggered_by,
        )
    )


def refresh_financial_ratios_from_latest_price(db: Session, company: Company) -> None:
    """Re-derives this company's FinancialRatios from its most recent real
    close price, so P/E and market cap stay consistent with real price even
    though revenue/profit/eps (the generator's `profile`) are still the demo
    generator's deterministic numbers, unchanged."""
    latest = (
        db.query(PriceHistory)
        .filter(PriceHistory.company_id == company.id)
        .order_by(PriceHistory.date.desc())
        .first()
    )
    if latest is None:
        return

    profile = generate_financial_profile(company.symbol)
    ratios = generate_ratios(company.symbol, profile, float(latest.close))

    existing_by_key = {
        (row.period_type, row.period_label): row
        for row in db.query(FinancialRatios).filter(FinancialRatios.company_id == company.id).all()
    }

    for r in ratios:
        row = existing_by_key.get((r.period_type, r.period_label))
        if row is None:
            row = FinancialRatios(company_id=company.id, period_type=r.period_type, period_label=r.period_label)
            db.add(row)

        row.fiscal_year = r.fiscal_year
        row.sequence = r.sequence
        row.pe_ratio = r.pe_ratio
        row.pb_ratio = r.pb_ratio
        row.roe = r.roe
        row.roce = r.roce
        row.debt_to_equity = r.debt_to_equity
        row.revenue_growth = r.revenue_growth
        row.profit_growth = r.profit_growth
        row.net_margin = r.net_margin
        row.market_cap = r.market_cap
