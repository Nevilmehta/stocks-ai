"""Deletes PriceHistory rows older than N years, across all companies.

The original 16 companies were backfilled with 5 years of history before the
retention window was shortened to 3 years - this trims that leftover older
data (and the synthetic 5-year price rows seed_market_data.py generates as
a placeholder for brand-new companies before the real backfill overwrites
the recent portion) so retention is consistent for every company.

Usage (from backend/, with venv activated):
    python scripts/prune_old_price_history.py [--years N]

DESTRUCTIVE - deletes real historical rows permanently. Take a DB backup
before running this (see backend/db_backups/ for the established pattern).
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import SessionLocal
from app.models.price_history import PriceHistory


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune PriceHistory rows older than N years.")
    parser.add_argument("--years", type=int, default=3, help="Retention window in years (default: 3).")
    args = parser.parse_args()

    cutoff = date.today() - timedelta(days=int(args.years * 365.25))

    db = SessionLocal()
    try:
        count = db.query(PriceHistory).filter(PriceHistory.date < cutoff).count()
        print(f"Found {count} PriceHistory rows older than {cutoff} ({args.years} years back).")
        if count == 0:
            print("Nothing to prune.")
            return

        deleted = db.query(PriceHistory).filter(PriceHistory.date < cutoff).delete(synchronize_session=False)
        db.commit()
        print(f"Deleted {deleted} rows older than {cutoff}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
