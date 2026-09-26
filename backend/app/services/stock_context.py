"""Builds the combined (detail + technicals + AI score) context used by
anything that needs a full picture of a stock - the AI providers, the
research router, and the compare router. Shared here so those routers don't
import "private" helpers from one another.
"""

from fastapi import HTTPException

from app.deps import ActiveStrategy
from app.providers.ai_provider import MarketOverviewContext, StockContext
from app.providers.market_data import MarketDataProvider
from app.routers.stocks import get_stock_ai_score, get_stock_detail, get_stock_technicals


def build_stock_context(symbol: str, provider: MarketDataProvider, active: ActiveStrategy) -> StockContext | None:
    try:
        detail = get_stock_detail(symbol, provider)
        technicals = get_stock_technicals(symbol, provider, active)
    except HTTPException:
        return None

    try:
        score = get_stock_ai_score(symbol, provider, active)
    except HTTPException:
        score = None

    return StockContext(detail=detail, technicals=technicals, score=score, strategy_name=active.name)


def build_market_overview_context(provider: MarketDataProvider, active: ActiveStrategy) -> MarketOverviewContext:
    overview = provider.get_market_overview()
    return MarketOverviewContext(
        as_of=overview.get("as_of"),
        total_companies=overview["total_companies"],
        advancers=overview["advancers"],
        decliners=overview["decliners"],
        top_gainers=overview["top_gainers"],
        top_losers=overview["top_losers"],
        strategy_name=active.name,
    )
