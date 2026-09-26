"""Merges CompanyFinancials + FinancialRatios into FinancialPeriod objects.

Its own leaf module (no dependency on any router) so it can be imported by
stocks.py, and by anything else that needs a company's financial history
(strategy preview/backtest) without risking a circular import with
stock_context.py, which itself imports from stocks.py.
"""

from __future__ import annotations

from app.providers.market_data import MarketDataProvider
from app.schemas.stock import FinancialPeriod


def build_financial_periods(provider: MarketDataProvider, symbol: str) -> list[FinancialPeriod]:
    """Merges CompanyFinancials + FinancialRatios rows into one FinancialPeriod per
    period, sorted oldest -> newest within each period_type (annual, then quarterly)."""
    financials = {(f.period_type, f.period_label): f for f in provider.get_financials(symbol)}
    ratios = {(r.period_type, r.period_label): r for r in provider.get_ratios(symbol)}

    periods: list[FinancialPeriod] = []
    for key, f in financials.items():
        r = ratios.get(key)
        periods.append(
            FinancialPeriod(
                period_type=f.period_type,
                period_label=f.period_label,
                fiscal_year=f.fiscal_year,
                revenue=float(f.revenue),
                net_profit=float(f.net_profit),
                operating_profit=float(f.operating_profit),
                eps=float(f.eps),
                operating_cash_flow=float(f.operating_cash_flow),
                total_debt=float(f.total_debt),
                pe_ratio=float(r.pe_ratio) if r else None,
                pb_ratio=float(r.pb_ratio) if r else None,
                roe=float(r.roe) if r else None,
                roce=float(r.roce) if r else None,
                debt_to_equity=float(r.debt_to_equity) if r else None,
                revenue_growth=float(r.revenue_growth) if r else None,
                profit_growth=float(r.profit_growth) if r else None,
                net_margin=float(r.net_margin) if r else None,
                market_cap=float(r.market_cap) if r else None,
            )
        )

    periods.sort(key=lambda p: (p.period_type, financials[(p.period_type, p.period_label)].sequence))
    return periods
