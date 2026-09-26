"""Deterministic DEMO DATA generators for price history, financials, and ratios.

Every company gets a reproducible synthetic profile derived from a hash of
its symbol, so re-running the seed script produces the same numbers. This is
NOT real market data - see app/seed/companies.py and the MARKET_DATA_PROVIDER
config flag. Values are stored in Rs. Crore for financials (matching how
Indian company results are normally reported) and Rs. per share for price/EPS.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

TRADING_DAYS_HISTORY_YEARS = 5


def _company_seed(symbol: str, salt: str) -> random.Random:
    return random.Random(f"stockai-demo-{symbol}-{salt}")


@dataclass
class OhlcvRow:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


def generate_price_history(symbol: str, years: int = TRADING_DAYS_HISTORY_YEARS) -> list[OhlcvRow]:
    """A seeded geometric random walk that produces plausible-looking daily OHLCV data."""
    rng = _company_seed(symbol, "price")
    base_price = rng.uniform(150, 4000)
    drift = rng.uniform(0.00015, 0.00045)  # slight long-run upward bias
    daily_vol = rng.uniform(0.012, 0.024)
    base_volume = rng.uniform(300_000, 6_000_000)

    end = date.today()
    start = end - timedelta(days=int(years * 365.25))

    rows: list[OhlcvRow] = []
    price = base_price
    current = start
    while current <= end:
        if current.weekday() < 5:  # Monday-Friday only
            change = rng.gauss(drift, daily_vol)
            open_price = price
            close_price = max(price * (1 + change), 1.0)
            high_price = max(open_price, close_price) * (1 + rng.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - rng.uniform(0, 0.01))
            volume = int(base_volume * rng.uniform(0.4, 1.8))

            rows.append(
                OhlcvRow(
                    trade_date=current,
                    open=round(open_price, 2),
                    high=round(high_price, 2),
                    low=round(low_price, 2),
                    close=round(close_price, 2),
                    volume=volume,
                )
            )
            price = close_price
        current += timedelta(days=1)

    return rows


@dataclass
class FinancialPeriodData:
    period_type: str  # "annual" | "quarterly"
    period_label: str
    fiscal_year: int
    sequence: int  # chronological order within period_type, 0 = oldest
    revenue: float
    net_profit: float
    operating_profit: float
    eps: float
    operating_cash_flow: float
    total_debt: float


@dataclass
class RatioPeriodData:
    period_type: str
    period_label: str
    fiscal_year: int
    sequence: int
    pe_ratio: float
    pb_ratio: float
    roe: float
    roce: float
    debt_to_equity: float
    revenue_growth: float
    profit_growth: float
    net_margin: float
    market_cap: float


@dataclass
class CompanyFinancialProfile:
    shares_outstanding_cr: float  # share count, in crores of shares
    periods: list[FinancialPeriodData]


def generate_financial_profile(symbol: str) -> CompanyFinancialProfile:
    """5 years of annual financials plus the trailing 8 quarters, DEMO DATA only."""
    rng = _company_seed(symbol, "financials")

    base_revenue_cr = rng.uniform(2_000, 150_000)
    revenue_growth = rng.uniform(0.04, 0.22)
    net_margin = rng.uniform(0.06, 0.24)
    op_margin = net_margin + rng.uniform(0.02, 0.08)
    debt_to_revenue = rng.uniform(0.15, 0.9)
    shares_outstanding_cr = rng.uniform(30, 650)

    current_year = date.today().year
    periods: list[FinancialPeriodData] = []

    revenue_for_year = base_revenue_cr
    for i in range(5):
        fiscal_year = current_year - (4 - i)
        if i > 0:
            revenue_for_year *= (1 + revenue_growth) * rng.uniform(0.85, 1.15)
        net_profit = revenue_for_year * net_margin * rng.uniform(0.9, 1.1)
        operating_profit = revenue_for_year * op_margin
        eps = (net_profit / shares_outstanding_cr) if shares_outstanding_cr else 0
        cash_flow = net_profit * rng.uniform(0.9, 1.3)
        debt = revenue_for_year * debt_to_revenue * rng.uniform(0.85, 1.15)

        periods.append(
            FinancialPeriodData(
                period_type="annual",
                period_label=f"FY{fiscal_year}",
                fiscal_year=fiscal_year,
                sequence=i,
                revenue=round(revenue_for_year, 2),
                net_profit=round(net_profit, 2),
                operating_profit=round(operating_profit, 2),
                eps=round(eps, 2),
                operating_cash_flow=round(cash_flow, 2),
                total_debt=round(debt, 2),
            )
        )

    latest_annual_revenue = periods[-1].revenue
    quarterly_base = latest_annual_revenue / 4
    for q in range(8, 0, -1):
        quarter_index = 8 - q
        fiscal_year = current_year - (quarter_index // 4)
        quarter_number = 4 - (quarter_index % 4)
        revenue_for_quarter = quarterly_base * rng.uniform(0.85, 1.15)
        net_profit = revenue_for_quarter * net_margin * rng.uniform(0.85, 1.15)
        operating_profit = revenue_for_quarter * op_margin
        eps = (net_profit / shares_outstanding_cr) if shares_outstanding_cr else 0
        cash_flow = net_profit * rng.uniform(0.8, 1.3)
        debt = revenue_for_quarter * 4 * debt_to_revenue * rng.uniform(0.85, 1.15)

        periods.append(
            FinancialPeriodData(
                period_type="quarterly",
                period_label=f"Q{quarter_number}FY{fiscal_year}",
                fiscal_year=fiscal_year,
                sequence=quarter_index,
                revenue=round(revenue_for_quarter, 2),
                net_profit=round(net_profit, 2),
                operating_profit=round(operating_profit, 2),
                eps=round(eps, 2),
                operating_cash_flow=round(cash_flow, 2),
                total_debt=round(debt, 2),
            )
        )

    return CompanyFinancialProfile(shares_outstanding_cr=shares_outstanding_cr, periods=periods)


def generate_ratios(
    symbol: str, profile: CompanyFinancialProfile, latest_price: float
) -> list[RatioPeriodData]:
    """Derives valuation/profitability ratios for every period in `profile`.

    Book value and capital-employed are backed out from a per-company target
    ROE/ROCE (drawn once, with light per-period jitter) rather than modeled
    as a separate balance-sheet - simple, deterministic, and good enough for
    demo data. `latest_price` (most recent close) is used for every period's
    P/E, P/B and market cap for the same reason: this is not meant to be a
    historically accurate valuation series, just a plausible current one.
    """
    rng = _company_seed(symbol, "ratios")
    roe_target = rng.uniform(0.10, 0.30)
    roce_target = rng.uniform(0.08, 0.26)
    shares = profile.shares_outstanding_cr

    annual_periods = [p for p in profile.periods if p.period_type == "annual"]
    quarterly_periods = [p for p in profile.periods if p.period_type == "quarterly"]

    ratios: list[RatioPeriodData] = []

    def _ratio_for(period: FinancialPeriodData, prev: FinancialPeriodData | None) -> RatioPeriodData:
        jitter = rng.uniform(0.92, 1.08)
        equity = period.net_profit / (roe_target * jitter) if roe_target else 0
        capital_employed = period.operating_profit / (roce_target * jitter) if roce_target else 0

        annualized_eps = period.eps if period.period_type == "annual" else period.eps * 4
        pe_ratio = min(latest_price / annualized_eps, 80.0) if annualized_eps > 0 else 0.0
        book_value_per_share = (equity / shares) if shares else 0.0
        pb_ratio = min(latest_price / book_value_per_share, 15.0) if book_value_per_share > 0 else 0.0
        debt_to_equity = (period.total_debt / equity) if equity > 0 else 0.0
        net_margin = (period.net_profit / period.revenue * 100) if period.revenue else 0.0
        market_cap = latest_price * shares

        revenue_growth = ((period.revenue - prev.revenue) / prev.revenue * 100) if prev and prev.revenue else 0.0
        profit_growth = (
            (period.net_profit - prev.net_profit) / abs(prev.net_profit) * 100
        ) if prev and prev.net_profit else 0.0

        return RatioPeriodData(
            period_type=period.period_type,
            period_label=period.period_label,
            fiscal_year=period.fiscal_year,
            sequence=period.sequence,
            pe_ratio=round(pe_ratio, 2),
            pb_ratio=round(pb_ratio, 2),
            roe=round((period.net_profit / equity * 100) if equity > 0 else 0.0, 2),
            roce=round((period.operating_profit / capital_employed * 100) if capital_employed > 0 else 0.0, 2),
            debt_to_equity=round(debt_to_equity, 2),
            revenue_growth=round(revenue_growth, 2),
            profit_growth=round(profit_growth, 2),
            net_margin=round(net_margin, 2),
            market_cap=round(market_cap, 2),
        )

    for i, period in enumerate(annual_periods):
        prev = annual_periods[i - 1] if i > 0 else None
        ratios.append(_ratio_for(period, prev))

    for i, period in enumerate(quarterly_periods):
        prev = quarterly_periods[i - 4] if i >= 4 else None
        ratios.append(_ratio_for(period, prev))

    return ratios
