"""Market data provider abstraction.

The rest of the app (routers, analytics) only ever talks to this interface,
never to a specific data source. Both `MockMarketDataProvider` and
`RealMarketDataProvider` just read whatever is in Postgres (`_DbMarketDataProvider`)
- the only real difference between "mock" and "real" is how that data got there:
scripts/seed_market_data.py's random walk, vs. app/services/market_data_sync.py's
NSE bhavcopy sync. Selected via the `MARKET_DATA_PROVIDER` env var, no router or
frontend changes needed either way.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.financials import CompanyFinancials, FinancialRatios
from app.models.price_history import PriceHistory

TIMEFRAME_DAYS: dict[str, int | None] = {
    "1D": 2,  # small buffer so a Monday/post-holiday request still finds the last trading day
    "1W": 8,
    "1M": 31,
    "3M": 93,
    "6M": 186,
    "1Y": 366,
    "3Y": 366 * 3,
    "MAX": None,
}


class MarketDataProvider(ABC):
    @abstractmethod
    def search_stocks(self, query: str, limit: int = 20) -> list[Company]: ...

    @abstractmethod
    def get_company(self, symbol: str) -> Company | None: ...

    @abstractmethod
    def get_price_history(self, symbol: str, timeframe: str = "1Y") -> list[PriceHistory]: ...

    @abstractmethod
    def get_financials(self, symbol: str) -> list[CompanyFinancials]: ...

    @abstractmethod
    def get_ratios(self, symbol: str) -> list[FinancialRatios]: ...

    @abstractmethod
    def get_market_overview(self) -> dict: ...

    @abstractmethod
    def get_companies_by_sector(self, sector: str, exclude_symbol: str | None = None) -> list[Company]: ...


class _DbMarketDataProvider(MarketDataProvider):
    """Shared read logic - just queries Postgres. Doesn't care whether the rows
    came from the demo seed generator or a real NSE sync; see module docstring."""

    def __init__(self, db: Session):
        self.db = db

    def search_stocks(self, query: str, limit: int = 20) -> list[Company]:
        q = query.strip()
        if not q:
            return self.db.query(Company).order_by(Company.name).limit(limit).all()

        like = f"%{q}%"
        return (
            self.db.query(Company)
            .filter(
                or_(
                    Company.symbol.ilike(like),
                    Company.name.ilike(like),
                    Company.sector.ilike(like),
                    Company.industry.ilike(like),
                )
            )
            .order_by(Company.name)
            .limit(limit)
            .all()
        )

    def get_company(self, symbol: str) -> Company | None:
        return self.db.query(Company).filter(Company.symbol == symbol.upper()).first()

    def get_price_history(self, symbol: str, timeframe: str = "1Y") -> list[PriceHistory]:
        company = self.get_company(symbol)
        if company is None:
            return []

        query = (
            self.db.query(PriceHistory)
            .filter(PriceHistory.company_id == company.id)
            .order_by(PriceHistory.date.asc())
        )

        days = TIMEFRAME_DAYS.get(timeframe.upper(), 366)
        if days is not None:
            cutoff = date.today() - timedelta(days=days)
            query = query.filter(PriceHistory.date >= cutoff)

        return query.all()

    def get_financials(self, symbol: str) -> list[CompanyFinancials]:
        company = self.get_company(symbol)
        if company is None:
            return []
        return (
            self.db.query(CompanyFinancials)
            .filter(CompanyFinancials.company_id == company.id)
            .order_by(CompanyFinancials.period_type, CompanyFinancials.sequence)
            .all()
        )

    def get_ratios(self, symbol: str) -> list[FinancialRatios]:
        company = self.get_company(symbol)
        if company is None:
            return []
        return (
            self.db.query(FinancialRatios)
            .filter(FinancialRatios.company_id == company.id)
            .order_by(FinancialRatios.period_type, FinancialRatios.sequence)
            .all()
        )

    def get_market_overview(self) -> dict:
        companies = self.db.query(Company).all()
        sector_counts: dict[str, int] = {}
        as_of = self.db.query(func.max(PriceHistory.date)).scalar()

        advancers = decliners = unchanged = 0
        movers: list[dict] = []
        for company in companies:
            sector_counts[company.sector] = sector_counts.get(company.sector, 0) + 1

            rows = (
                self.db.query(PriceHistory)
                .filter(PriceHistory.company_id == company.id)
                .order_by(PriceHistory.date.desc())
                .limit(2)
                .all()
            )
            if len(rows) < 2:
                continue
            latest, previous = rows[0], rows[1]
            if latest.close > previous.close:
                advancers += 1
            elif latest.close < previous.close:
                decliners += 1
            else:
                unchanged += 1

            if previous.close:
                change_percent = float((latest.close - previous.close) / previous.close * 100)
                movers.append(
                    {
                        "symbol": company.symbol,
                        "name": company.name,
                        "sector": company.sector,
                        "latest_price": float(latest.close),
                        "change_percent": round(change_percent, 2),
                    }
                )

        movers.sort(key=lambda m: m["change_percent"], reverse=True)
        top_gainers = [m for m in movers if m["change_percent"] > 0][:5]
        top_losers = list(reversed([m for m in movers if m["change_percent"] < 0][-5:]))

        return {
            "total_companies": len(companies),
            "sectors": len(sector_counts),
            "sector_breakdown": [
                {"sector": sector, "count": count} for sector, count in sorted(sector_counts.items())
            ],
            "advancers": advancers,
            "decliners": decliners,
            "unchanged": unchanged,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "as_of": as_of,  # not part of the MarketOverview response schema - extra keys are
            # ignored there; used internally by research.py to ground "when was this updated"
            # chat answers with a real date.
        }

    def get_companies_by_sector(self, sector: str, exclude_symbol: str | None = None) -> list[Company]:
        # "Unclassified" isn't a real sector - it's the catch-all for every
        # company with no Nifty index match (~2,000+ of the ~2,660 NSE
        # universe). Treating that bucket as "peers" for valuation comparison
        # is both meaningless (comparing P/E against random unrelated
        # companies isn't a real peer comparison) and, at that size, a real
        # performance problem (every AI-score computation would pull and
        # score thousands of "peers"). Real sectors are capped at a sample
        # size that's still a meaningful average without unbounded cost.
        if sector == "Unclassified":
            return []
        query = self.db.query(Company).filter(Company.sector == sector)
        if exclude_symbol:
            query = query.filter(Company.symbol != exclude_symbol.upper())
        return query.order_by(Company.name).limit(15).all()


class MockMarketDataProvider(_DbMarketDataProvider):
    """Reads DEMO DATA seeded into Postgres by scripts/seed_market_data.py."""


class RealMarketDataProvider(_DbMarketDataProvider):
    """Reads real NSE price history synced into Postgres by
    app/services/market_data_sync.py (backfilled via scripts/sync_real_market_data.py,
    kept current by app/scheduler.py). Financials/ratios are still the demo
    generator's numbers, re-priced against the real latest close - see
    market_data_sync.refresh_financial_ratios_from_latest_price."""
