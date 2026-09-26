"""Backfills real NSE price history for every seeded company. NSE publishes
one bhavcopy file per trading day covering all listed stocks, so this makes
one request per weekday (not per company).

Usage (from backend/, with venv activated):
    python scripts/sync_real_market_data.py [--years N]

Idempotent: each day's data is upserted, not duplicated, so it's safe to
interrupt and re-run. Takes roughly 6-8 minutes for the default 5-year
backfill (~1250 requests, with a short delay between requests to avoid
tripping NSE's bot-rate detection).
"""

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import SessionLocal
from app.models.company import Company
from app.services.market_data_sync import refresh_financial_ratios_from_latest_price, sync_price_history_for_date

REQUEST_DELAY_SECONDS = 0.3


def weekdays_between(start: date, end: date):
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday-Friday only
            yield current
        current += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill real NSE price history.")
    parser.add_argument("--years", type=int, default=5, help="How many years back to backfill (default: 5).")
    args = parser.parse_args()

    end = date.today()
    start = end - timedelta(days=int(args.years * 365.25))

    db = SessionLocal()
    try:
        companies = db.query(Company).all()
        if not companies:
            print("No companies found - run scripts/seed_data.py first.")
            return

        print(f"== Backfilling real NSE price history, {start} to {end} ({len(companies)} companies) ==")

        total_days = 0
        total_rows = 0
        for trade_date in weekdays_between(start, end):
            try:
                rows_synced = sync_price_history_for_date(db, trade_date)
            except Exception as exc:
                print(f"[error] {trade_date}: {exc}")
                db.rollback()
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            db.commit()
            if rows_synced:
                total_days += 1
                total_rows += rows_synced
                print(f"[synced] {trade_date}: {rows_synced} companies")
            time.sleep(REQUEST_DELAY_SECONDS)

        print(f"\nPrice history done: {total_days} trading days, {total_rows} company-day rows.")

        print("Refreshing financial ratios against latest real price...")
        for company in companies:
            refresh_financial_ratios_from_latest_price(db, company)
        db.commit()
    finally:
        db.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
