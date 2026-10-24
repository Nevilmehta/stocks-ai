from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import ActiveStrategy, get_active_strategy, get_current_user, get_market_data_provider
from app.providers.market_data import MarketDataProvider
from app.routers.stocks import get_stock_ai_score, get_stock_detail
from app.schemas.screener import ScreenerRow

router = APIRouter(prefix="/api/screener", tags=["screener"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ScreenerRow])
def run_screener(
    sector: str | None = Query(None),
    market_cap_min: float | None = Query(None),
    pe_max: float | None = Query(None),
    roe_min: float | None = Query(None),
    roce_min: float | None = Query(None),
    debt_to_equity_max: float | None = Query(None),
    revenue_growth_min: float | None = Query(None),
    profit_growth_min: float | None = Query(None),
    ai_score_min: int | None = Query(None),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> list[ScreenerRow]:
    """Evaluates candidate companies against the given thresholds with a
    simple in-memory filter - no query builder needed, but even just building
    a StockDetail (let alone a full AI score) is real per-company work, so
    the candidate list itself is capped at MAX_CANDIDATES *before* either
    stage runs - otherwise an unfiltered request against the full ~2,660
    company NSE universe would do thousands of detail/score computations
    synchronously in one request. A sector filter is applied first (DB-level,
    cheap), so filtering by sector sees every company in that sector, not a
    truncated slice of the whole universe."""
    MAX_CANDIDATES = 150
    companies = provider.search_stocks("", limit=5000)
    if sector:
        companies = [c for c in companies if c.sector == sector]
    companies = companies[:MAX_CANDIDATES]

    rows: list[ScreenerRow] = []
    for company in companies:
        detail = get_stock_detail(company.symbol, provider)

        if market_cap_min is not None and (detail.market_cap is None or detail.market_cap < market_cap_min):
            continue
        if pe_max is not None and (detail.pe_ratio is None or detail.pe_ratio > pe_max):
            continue
        if roe_min is not None and (detail.roe is None or detail.roe < roe_min):
            continue
        if roce_min is not None and (detail.roce is None or detail.roce < roce_min):
            continue
        if debt_to_equity_max is not None and (
            detail.debt_to_equity is None or detail.debt_to_equity > debt_to_equity_max
        ):
            continue
        if revenue_growth_min is not None and (
            detail.revenue_growth is None or detail.revenue_growth < revenue_growth_min
        ):
            continue
        if profit_growth_min is not None and (
            detail.profit_growth is None or detail.profit_growth < profit_growth_min
        ):
            continue

        try:
            score = get_stock_ai_score(company.symbol, provider, active)
        except HTTPException:
            score = None
        if ai_score_min is not None and (score is None or score.overall_score < ai_score_min):
            continue

        rows.append(
            ScreenerRow(
                symbol=detail.symbol,
                name=detail.name,
                sector=detail.sector,
                latest_price=detail.latest_price,
                change_percent=detail.change_percent,
                volume=detail.volume,
                market_cap=detail.market_cap,
                pe_ratio=detail.pe_ratio,
                roe=detail.roe,
                roce=detail.roce,
                debt_to_equity=detail.debt_to_equity,
                revenue_growth=detail.revenue_growth,
                profit_growth=detail.profit_growth,
                ai_score=score.overall_score if score else None,
                ai_label=score.label if score else None,
            )
        )

    rows.sort(key=lambda r: r.ai_score if r.ai_score is not None else -1, reverse=True)
    return rows
