"""Expands the company universe from the original 16 hand-picked large-caps
to every NSE-listed equity, using the daily bhavcopy file itself as the
company master list (no separate "equity list" source needed - a bhavcopy
already contains every actively-traded symbol + company name) plus NSE's
free Nifty index constituent lists for sector classification and index
membership.

Usage (from backend/, with venv activated):
    python scripts/seed_all_nse_companies.py

Idempotent: existing companies (the original 16 + TMCV/TMPV) keep their
hand-written name/description, only sector/industry/index_memberships get
refreshed from the same Nifty-derived data as everyone else, for a
consistent taxonomy across the whole app. New companies get a generic
description and a title-cased name derived from the bhavcopy's (all-caps,
sometimes abbreviated) company name field.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import Base, SessionLocal, engine
from app.models.company import Company
from app.services.nifty_indices import build_sector_and_index_maps
from app.services.nse_bhavcopy import fetch_bhavcopy

MAX_LOOKBACK_DAYS = 10


def _fetch_latest_company_universe() -> dict[str, str]:
    """Walks back from today to find the most recent available bhavcopy
    (today's may not be published yet, or today/recent days may be
    holidays/weekends) and returns {symbol: raw_name}."""
    current = date.today()
    for _ in range(MAX_LOOKBACK_DAYS):
        rows = fetch_bhavcopy(current)
        if rows:
            return {row.symbol: row.name for row in rows if row.symbol}
        current -= timedelta(days=1)
    raise RuntimeError(f"No bhavcopy found in the last {MAX_LOOKBACK_DAYS} days - is NSE reachable?")


def _display_name(raw_name: str, symbol: str) -> str:
    return raw_name.title() if raw_name else symbol.title()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Fetching the current NSE equity universe from the latest bhavcopy...")
        universe = _fetch_latest_company_universe()
        print(f"Found {len(universe)} actively-traded EQ symbols.")

        print("Fetching Nifty index constituent lists for sector + index membership...")
        sector_by_symbol, indices_by_symbol = build_sector_and_index_maps()
        print(f"Got sector/index data for {len(sector_by_symbol)} symbols across all Nifty lists.")

        existing_by_symbol = {c.symbol: c for c in db.query(Company).all()}

        created = 0
        updated = 0
        for symbol, raw_name in universe.items():
            sector = sector_by_symbol.get(symbol, "Unclassified")
            indices = indices_by_symbol.get(symbol, [])

            existing = existing_by_symbol.get(symbol)
            if existing is not None:
                # Refresh sector + index membership for consistency, but never
                # touch name/description/industry - the original 16 (+TMCV/TMPV)
                # have hand-written, more specific values than Nifty's single
                # broad "Industry" column (e.g. "Private Sector Bank" instead
                # of just "Financial Services") that would be a downgrade to
                # overwrite.
                existing.sector = sector
                existing.index_memberships = indices
                updated += 1
                continue

            name = _display_name(raw_name, symbol)
            db.add(
                Company(
                    symbol=symbol,
                    name=name,
                    exchange="NSE",
                    sector=sector,
                    industry=sector,
                    description=f"{name} is listed on the NSE" + (f" ({sector})." if sector != "Unclassified" else "."),
                    index_memberships=indices,
                )
            )
            created += 1

            if created % 500 == 0:
                db.commit()
                print(f"  ...{created} new companies created so far")

        db.commit()
        print(f"\nDone. Created {created} new companies, refreshed sector/index data for {updated} existing ones.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
