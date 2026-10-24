from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics import technicals as ta
from app.analytics.indicators_service import compute_technical_indicators
from app.analytics.scoring import compute_ai_score
from app.database import get_db
from app.deps import ActiveStrategy, get_active_strategy, get_current_user, get_market_data_provider
from app.models.company import Company
from app.models.financials import PeriodType
from app.providers.market_data import TIMEFRAME_DAYS, MarketDataProvider
from app.schemas.company import CompanyPublic
from app.schemas.stock import (
    AIScore,
    AIScoreSubscores,
    FinancialPeriod,
    IntradayHistory,
    IntradayPoint,
    MarketOverview,
    PricePoint,
    StockDetail,
    TechnicalIndicators,
)
from app.services.financial_periods import build_financial_periods
from app.services.intraday_data import fetch_latest_intraday_session

router = APIRouter(prefix="/api/stocks", tags=["stocks"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CompanyPublic])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    """Full company listing, used by the dashboard."""
    return db.query(Company).order_by(Company.name).all()


@router.get("/search", response_model=list[CompanyPublic])
def search_stocks(
    q: str = Query("", description="Symbol, name, sector or industry"),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> list[Company]:
    return provider.search_stocks(q)


@router.get("/overview", response_model=MarketOverview)
def market_overview(provider: MarketDataProvider = Depends(get_market_data_provider)) -> MarketOverview:
    return MarketOverview(**provider.get_market_overview())


@router.get("/{symbol}", response_model=StockDetail)
def get_stock_detail(
    symbol: str, provider: MarketDataProvider = Depends(get_market_data_provider)
) -> StockDetail:
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    price_rows = provider.get_price_history(symbol, timeframe="1Y")
    latest_price = previous_close = change = change_percent = as_of = volume = None
    if price_rows:
        latest_price = float(price_rows[-1].close)
        as_of = price_rows[-1].date
        volume = price_rows[-1].volume
        if len(price_rows) >= 2:
            previous_close = float(price_rows[-2].close)
            change = latest_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else None

    highs = [float(r.high) for r in price_rows]
    lows = [float(r.low) for r in price_rows]
    week52_high, week52_low = ta.fifty_two_week_high_low(highs, lows) if price_rows else (None, None)

    annual_ratios = [r for r in provider.get_ratios(symbol) if r.period_type == PeriodType.annual]
    latest_ratio = annual_ratios[-1] if annual_ratios else None

    annual_financials = [f for f in provider.get_financials(symbol) if f.period_type == PeriodType.annual]
    latest_financials = annual_financials[-1] if annual_financials else None

    return StockDetail(
        id=company.id,
        symbol=company.symbol,
        name=company.name,
        exchange=company.exchange,
        sector=company.sector,
        industry=company.industry,
        description=company.description,
        index_memberships=company.index_memberships,
        latest_price=latest_price,
        previous_close=previous_close,
        change=round(change, 2) if change is not None else None,
        change_percent=round(change_percent, 2) if change_percent is not None else None,
        as_of=as_of,
        market_cap=float(latest_ratio.market_cap) if latest_ratio else None,
        pe_ratio=float(latest_ratio.pe_ratio) if latest_ratio else None,
        pb_ratio=float(latest_ratio.pb_ratio) if latest_ratio else None,
        roe=float(latest_ratio.roe) if latest_ratio else None,
        roce=float(latest_ratio.roce) if latest_ratio else None,
        eps=float(latest_financials.eps) if latest_financials else None,
        debt_to_equity=float(latest_ratio.debt_to_equity) if latest_ratio else None,
        revenue_growth=float(latest_ratio.revenue_growth) if latest_ratio else None,
        profit_growth=float(latest_ratio.profit_growth) if latest_ratio else None,
        week52_high=week52_high,
        week52_low=week52_low,
        volume=volume,
    )


@router.get("/{symbol}/history", response_model=list[PricePoint])
def get_stock_history(
    symbol: str,
    range: str = Query("1Y", description=f"One of {list(TIMEFRAME_DAYS)}"),
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> list[PricePoint]:
    if range.upper() not in TIMEFRAME_DAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid range '{range}'")

    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    rows = provider.get_price_history(symbol, timeframe=range)
    return [
        PricePoint(
            date=row.date,
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=row.volume,
        )
        for row in rows
    ]


@router.get("/{symbol}/peers", response_model=list[CompanyPublic])
def get_stock_peers(
    symbol: str, provider: MarketDataProvider = Depends(get_market_data_provider)
) -> list[Company]:
    """Same-sector companies, for the stock page's Peers tab. Reuses
    `get_companies_by_sector` (already capped, already treats the
    "Unclassified" bucket as peer-less - see its own docstring) instead of
    having the frontend fetch the full ~2,660-company list and filter
    client-side, which was real, measurable waste: ~446KB transferred and
    parsed on every single stock page visit just to find 2-3 peers."""
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return provider.get_companies_by_sector(company.sector, exclude_symbol=symbol)


@router.get("/{symbol}/intraday", response_model=IntradayHistory)
def get_stock_intraday(
    symbol: str, provider: MarketDataProvider = Depends(get_market_data_provider)
) -> IntradayHistory:
    """Real 1-minute bars for the most recent NSE trading session, fetched
    live from Yahoo Finance's unofficial chart API (see
    app/services/intraday_data.py's module docstring for what was verified
    before building this and its real limitations). Deliberately not stored
    in PriceHistory - this is a fetch-on-demand view of the last few days
    only, not a historical archive, and the source can't be hammered in bulk
    anyway. `points` is simply empty (not a 404) when Yahoo has no usable
    data for this symbol - not every NSE company is reachable this way, and
    that's a normal, expected outcome here, not an error."""
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    result = fetch_latest_intraday_session(company.symbol)
    if result is None:
        return IntradayHistory(trading_date=None, points=[])

    trading_date, bars = result
    return IntradayHistory(
        trading_date=trading_date,
        points=[
            IntradayPoint(time=bar.time, open=bar.open, high=bar.high, low=bar.low, close=bar.close, volume=bar.volume)
            for bar in bars
        ],
    )


@router.get("/{symbol}/financials", response_model=list[FinancialPeriod])
def get_stock_financials(
    symbol: str, provider: MarketDataProvider = Depends(get_market_data_provider)
) -> list[FinancialPeriod]:
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    return build_financial_periods(provider, symbol)


@router.get("/{symbol}/technicals", response_model=TechnicalIndicators)
def get_stock_technicals(
    symbol: str,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> TechnicalIndicators:
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # "1Y" (not "MAX") - matches get_stock_ai_score's own reasoning just
    # below: every indicator this computes (up to SMA_200/EMA_200, 60-day
    # Fibonacci lookback) needs at most ~252 trading days, and fetching/
    # processing the full up-to-3-year history here was pure extra cost on
    # every single stock-page view for zero accuracy benefit.
    rows = provider.get_price_history(symbol, timeframe="1Y")
    return compute_technical_indicators(rows, active.config)


@router.get("/{symbol}/ai-score", response_model=AIScore)
def get_stock_ai_score(
    symbol: str,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> AIScore:
    """Deterministic AI Research Score - see analytics/scoring.py. Not generated
    by an AI model; an AI provider only ever explains this score, in a later phase."""
    company = provider.get_company(symbol)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    config = active.config
    annual_periods = [p for p in build_financial_periods(provider, symbol) if p.period_type == PeriodType.annual]

    # "1Y" (not "MAX") - every indicator the score uses (up to SMA_200/52-week
    # range) needs at most ~252 trading days; fetching the full 3-year window
    # here would roughly double the data/CPU cost of every AI-score call for
    # no accuracy benefit, which matters a lot once this runs per-company
    # across the full ~2,660-company universe (screener, strategy preview).
    price_rows = provider.get_price_history(symbol, timeframe="1Y")
    technicals = compute_technical_indicators(price_rows, config)

    peer_companies = provider.get_companies_by_sector(company.sector, exclude_symbol=symbol)
    peer_latest_periods: list[FinancialPeriod] = []
    for peer in peer_companies:
        peer_annual = [p for p in build_financial_periods(provider, peer.symbol) if p.period_type == PeriodType.annual]
        if peer_annual:
            peer_latest_periods.append(peer_annual[-1])

    result = compute_ai_score(annual_periods, technicals, peer_latest_periods, config)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enough financial data to compute an AI Research Score for this stock.",
        )

    return AIScore(
        symbol=company.symbol,
        as_of=technicals.as_of,
        overall_score=result.overall_score,
        label=result.label,
        risk_label=result.risk_label,
        subscores=AIScoreSubscores(
            financial_strength=result.financial_strength,
            growth=result.growth,
            profitability=result.profitability,
            valuation=result.valuation,
            technical_momentum=result.technical_momentum,
            risk=result.risk,
        ),
        methodology_note=(
            f"Computed deterministically from financial ratios, growth trends, and technical "
            f"indicators under the '{active.name}' strategy - weighted "
            f"{config.weight_financial_strength:.0%} Financial Strength, {config.weight_growth:.0%} Growth, "
            f"{config.weight_profitability:.0%} Profitability, {config.weight_valuation:.0%} Valuation, "
            f"{config.weight_technical_momentum:.0%} Technical Momentum, {config.weight_risk:.0%} Risk. "
            "This is a research score, not personalized investment advice."
        ),
    )
