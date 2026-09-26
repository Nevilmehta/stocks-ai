"""Seed DEMO price history, financials, and ratios for every seeded company.

Usage (from backend/, with venv activated):
    python scripts/seed_market_data.py

Idempotent: skips a company if it already has price history. Re-run after
deleting rows (or truncating the tables) to regenerate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import Base, SessionLocal, engine
from app.models.company import Company
from app.models.financials import CompanyFinancials, FinancialRatios
from app.models.price_history import PriceHistory
from app.seed.market_data import generate_financial_profile, generate_price_history, generate_ratios


def seed_company_market_data(db, company: Company) -> None:
    existing = db.query(PriceHistory).filter(PriceHistory.company_id == company.id).first()
    if existing is not None:
        print(f"[skip] {company.symbol} already has price history")
        return

    price_rows = generate_price_history(company.symbol)
    db.bulk_save_objects(
        [
            PriceHistory(
                company_id=company.id,
                date=row.trade_date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in price_rows
        ]
    )

    latest_price = price_rows[-1].close
    profile = generate_financial_profile(company.symbol)

    db.bulk_save_objects(
        [
            CompanyFinancials(
                company_id=company.id,
                period_type=p.period_type,
                period_label=p.period_label,
                fiscal_year=p.fiscal_year,
                sequence=p.sequence,
                revenue=p.revenue,
                net_profit=p.net_profit,
                operating_profit=p.operating_profit,
                eps=p.eps,
                operating_cash_flow=p.operating_cash_flow,
                total_debt=p.total_debt,
            )
            for p in profile.periods
        ]
    )

    ratios = generate_ratios(company.symbol, profile, latest_price)
    db.bulk_save_objects(
        [
            FinancialRatios(
                company_id=company.id,
                period_type=r.period_type,
                period_label=r.period_label,
                fiscal_year=r.fiscal_year,
                sequence=r.sequence,
                pe_ratio=r.pe_ratio,
                pb_ratio=r.pb_ratio,
                roe=r.roe,
                roce=r.roce,
                debt_to_equity=r.debt_to_equity,
                revenue_growth=r.revenue_growth,
                profit_growth=r.profit_growth,
                net_margin=r.net_margin,
                market_cap=r.market_cap,
            )
            for r in ratios
        ]
    )

    db.commit()
    print(
        f"[created] {company.symbol}: {len(price_rows)} price rows, "
        f"{len(profile.periods)} financial periods, {len(ratios)} ratio periods "
        f"(latest close Rs.{latest_price})"
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        companies = db.query(Company).order_by(Company.symbol).all()
        if not companies:
            print("No companies found - run scripts/seed_data.py first.")
            return

        print(f"== Seeding DEMO market data for {len(companies)} companies ==")
        for company in companies:
            seed_company_market_data(db, company)
    finally:
        db.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
