from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.analytics import technicals as ta
from app.analytics.indicators_service import compute_technical_indicators
from app.deps import ActiveStrategy, get_active_strategy, get_current_user, get_market_data_provider
from app.models.financials import PeriodType
from app.providers.market_data import MarketDataProvider
from app.schemas.smart_indicator import IndicatorOption, SmartIndicatorMeta, SmartIndicatorRow
from app.schemas.stock import TechnicalIndicators
from app.schemas.strategy import IndicatorKey, StrategyConfig

router = APIRouter(prefix="/api/smart-indicator", tags=["smart-indicator"], dependencies=[Depends(get_current_user)])

# Same shape as screener.py's MAX_CANDIDATES: computing a full technicals
# pass (now including swing/Fibonacci) for the whole ~2,660-company NSE
# universe synchronously in one request isn't viable, so the candidate list
# is capped before the per-company work runs.
MAX_CANDIDATES = 150

# Priority order used only for display (meta's available_indicators list) -
# "overall" always leads since it's the always-on, default-of-defaults view.
_PRIORITY: list[IndicatorKey] = ["rsi", "sma", "ema", "macd", "bollinger", "fibonacci"]

_ENABLE_ATTR: dict[str, str] = {
    "sma": "enable_sma",
    "ema": "enable_ema",
    "rsi": "enable_rsi",
    "macd": "enable_macd",
    "bollinger": "enable_bollinger",
    "fibonacci": "enable_fibonacci",
}

_INDICATOR_LABELS: dict[IndicatorKey, str] = {
    "overall": "Overall",
    "sma": "SMA",
    "ema": "EMA",
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "Bollinger Bands",
    "fibonacci": "Fibonacci",
}

# Indicators where a SMALLER value is more interesting (closest to a level -
# a potential inflection point) - everything else (including "overall", a
# vote count) sorts with the largest value first (strongest reading).
_SORT_ASCENDING: set[IndicatorKey] = {"fibonacci", "bollinger"}


def resolve_indicator(config: StrategyConfig, explicit: IndicatorKey | None) -> IndicatorKey:
    """Picks which indicator drives the Smart Indicator page's sort/value
    column. "overall" is always valid - it's not gated by any single
    enable_* flag, it just combines whichever of the other 6 are currently
    enabled (see _overall_score). An explicit request for one of the other 6
    while it's disabled is rejected outright (never silently substituted -
    same "state the adjustment plainly" rule this app already follows for
    historical price lookups). No explicit request falls back from the
    admin's configured default to "overall" if that default happens to be a
    currently-disabled indicator - "overall" is always a safe, meaningful
    fallback since it degrades gracefully to 0 enabled indicators on its
    own."""
    if explicit is not None:
        if explicit != "overall" and not getattr(config, _ENABLE_ATTR[explicit]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The '{explicit}' indicator is not currently enabled by the admin.",
            )
        return explicit

    default = config.default_smart_indicator
    if default == "overall" or getattr(config, _ENABLE_ATTR[default]):
        return default
    return "overall"


def _bollinger_band_proximity(latest_price: float, technicals: TechnicalIndicators) -> float | None:
    """% distance from whichever Bollinger band is nearer - a smart-indicator
    -list-only convenience (ranking 150 candidates), not generally useful
    enough on a single stock's page to belong in the shared TechnicalIndicators
    schema the way price-vs-SMA/EMA already is."""
    upper, lower = technicals.bollinger_upper, technicals.bollinger_lower
    if upper is None or lower is None or not latest_price:
        return None
    return round(min(abs(latest_price - upper), abs(latest_price - lower)) / latest_price * 100, 2)


def _overall_score(
    config: StrategyConfig, technicals: TechnicalIndicators, latest_price: float
) -> tuple[float | None, str]:
    """Combines whichever of the 6 indicators the admin currently has
    enabled into one +1/0/-1-per-indicator vote, summed. Disabled indicators
    are skipped entirely (not counted as 0 - excluded from the denominator
    too), so "Overall" always reflects exactly the admin's current
    configuration, nothing more. Fibonacci is deliberately never part of the
    vote - same reasoning as derive_trade_signal() (app/analytics/signal.py):
    there's no non-arbitrary "near a level" threshold to vote with, so it
    stays informational-only everywhere in this app, not just here."""
    votes: list[int] = []

    if config.enable_rsi and technicals.rsi_14 is not None:
        if technicals.rsi_14 < config.rsi_oversold:
            votes.append(1)
        elif technicals.rsi_14 > config.rsi_overbought:
            votes.append(-1)
        else:
            votes.append(0)

    if config.enable_sma and technicals.price_vs_sma50_percent is not None and technicals.price_vs_sma200_percent is not None:
        if technicals.price_vs_sma50_percent > 0 and technicals.price_vs_sma200_percent > 0:
            votes.append(1)
        elif technicals.price_vs_sma50_percent < 0 and technicals.price_vs_sma200_percent < 0:
            votes.append(-1)
        else:
            votes.append(0)

    if config.enable_ema and technicals.price_vs_ema50_percent is not None and technicals.price_vs_ema200_percent is not None:
        if technicals.price_vs_ema50_percent > 0 and technicals.price_vs_ema200_percent > 0:
            votes.append(1)
        elif technicals.price_vs_ema50_percent < 0 and technicals.price_vs_ema200_percent < 0:
            votes.append(-1)
        else:
            votes.append(0)

    if config.enable_macd and technicals.macd_histogram is not None:
        votes.append(1 if technicals.macd_histogram > 0 else (-1 if technicals.macd_histogram < 0 else 0))

    if config.enable_bollinger and technicals.bollinger_upper is not None and technicals.bollinger_lower is not None:
        if latest_price < technicals.bollinger_lower:
            votes.append(1)
        elif latest_price > technicals.bollinger_upper:
            votes.append(-1)
        else:
            votes.append(0)

    if not votes:
        return None, "Overall score unavailable"
    label = f"Overall ({len(votes)} indicator{'s' if len(votes) != 1 else ''})"
    return float(sum(votes)), label


def _indicator_value_and_label(
    indicator: IndicatorKey, config: StrategyConfig, technicals: TechnicalIndicators, latest_price: float
) -> tuple[float | None, str]:
    if indicator == "overall":
        return _overall_score(config, technicals, latest_price)
    if indicator == "rsi":
        return technicals.rsi_14, f"RSI ({config.rsi_period})"
    if indicator == "fibonacci":
        return technicals.nearest_fibonacci_distance_percent, "Fib. distance %"
    if indicator == "sma":
        return technicals.price_vs_sma50_percent, f"vs SMA{config.sma_medium} %"
    if indicator == "ema":
        return technicals.price_vs_ema50_percent, f"vs EMA{config.ema_medium} %"
    if indicator == "macd":
        return technicals.macd_histogram, "MACD histogram"
    return _bollinger_band_proximity(latest_price, technicals), "Band proximity %"


def _sort_rows(rows: list[SmartIndicatorRow], indicator: IndicatorKey) -> list[SmartIndicatorRow]:
    with_value = [r for r in rows if r.indicator_value is not None]
    without_value = [r for r in rows if r.indicator_value is None]

    if indicator == "rsi":
        with_value.sort(key=lambda r: abs(r.indicator_value - 50), reverse=True)
    elif indicator in _SORT_ASCENDING:
        with_value.sort(key=lambda r: r.indicator_value)
    else:
        with_value.sort(key=lambda r: r.indicator_value, reverse=True)

    return with_value + without_value


@router.get("/meta", response_model=SmartIndicatorMeta)
def smart_indicator_meta(active: ActiveStrategy = Depends(get_active_strategy)) -> SmartIndicatorMeta:
    """Which indicators the admin has enabled (so the frontend can render
    exactly those as selectable views - customers can switch between
    admin-enabled indicators but never see or pick one admin has turned
    off), and which one is the default."""
    available = [IndicatorOption(key="overall", label=_INDICATOR_LABELS["overall"])] + [
        IndicatorOption(key=key, label=_INDICATOR_LABELS[key])
        for key in _PRIORITY
        if getattr(active.config, _ENABLE_ATTR[key])
    ]
    return SmartIndicatorMeta(
        available_indicators=available,
        default_indicator=resolve_indicator(active.config, None),
    )


@router.get("", response_model=list[SmartIndicatorRow])
def run_smart_indicator(
    sector: str | None = Query(None),
    indicator: IndicatorKey | None = Query(None, description="Which indicator's view to show"),
    signal: str | None = Query(None, description="buy, sell or neutral"),
    rsi_state: str | None = Query(None, description="oversold, overbought or any"),
    trend_structure: str | None = Query(None, description="uptrend, downtrend, sideways or any"),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    active: ActiveStrategy = Depends(get_active_strategy),
) -> list[SmartIndicatorRow]:
    """Every tracked company scored under the currently-active strategy's
    indicator rules. Fetches price history once per candidate and derives
    both the price/volume/return fields and the full technicals (including
    the new swing-structure/Fibonacci/signal fields) from that single fetch -
    deliberately does NOT call get_stock_detail/get_stock_technicals, since
    each of those independently hits get_price_history and would double the
    DB cost at MAX_CANDIDATES scale (the same anti-pattern already flagged in
    get_stock_ai_score's own comments).

    `indicator` controls which value sorts the list and which column it's
    shown as (see resolve_indicator); `sector`/`signal`/`rsi_state`/
    `trend_structure` remain orthogonal filters that narrow the set
    regardless of which indicator view is active."""
    resolved_indicator = resolve_indicator(active.config, indicator)

    companies = provider.search_stocks("", limit=5000)
    if sector:
        companies = [c for c in companies if c.sector == sector]
    companies = companies[:MAX_CANDIDATES]

    rows: list[SmartIndicatorRow] = []
    for company in companies:
        price_rows = provider.get_price_history(company.symbol, timeframe="1Y")
        if not price_rows:
            continue

        closes = [float(r.close) for r in price_rows]
        latest_price = closes[-1]
        change_percent = (
            round((closes[-1] - closes[-2]) / closes[-2] * 100, 2)
            if len(closes) >= 2 and closes[-2]
            else None
        )
        volume = price_rows[-1].volume
        return_1d = ta.period_return(closes, 1)
        return_1w = ta.period_return(closes, 5)

        technicals = compute_technical_indicators(price_rows, active.config)

        if signal and technicals.signal != signal:
            continue
        if rsi_state == "oversold" and (
            technicals.rsi_14 is None or technicals.rsi_14 >= active.config.rsi_oversold
        ):
            continue
        if rsi_state == "overbought" and (
            technicals.rsi_14 is None or technicals.rsi_14 <= active.config.rsi_overbought
        ):
            continue
        if trend_structure == "uptrend" and "Uptrend" not in technicals.swing_structure:
            continue
        if trend_structure == "downtrend" and "Downtrend" not in technicals.swing_structure:
            continue
        if trend_structure == "sideways" and technicals.swing_structure != "Sideways / Mixed":
            continue

        annual_ratios = [r for r in provider.get_ratios(company.symbol) if r.period_type == PeriodType.annual]
        latest_ratio = annual_ratios[-1] if annual_ratios else None
        pe_ratio = float(latest_ratio.pe_ratio) if latest_ratio and latest_ratio.pe_ratio is not None else None

        indicator_value, indicator_label = _indicator_value_and_label(
            resolved_indicator, active.config, technicals, latest_price
        )

        rows.append(
            SmartIndicatorRow(
                symbol=company.symbol,
                name=company.name,
                sector=company.sector,
                latest_price=round(latest_price, 2),
                change_percent=change_percent,
                volume=volume,
                return_1d=round(return_1d, 2) if return_1d is not None else None,
                return_1w=round(return_1w, 2) if return_1w is not None else None,
                return_1m=technicals.return_1m,
                pe_ratio=pe_ratio,
                rsi_14=technicals.rsi_14,
                trend=technicals.trend,
                swing_structure=technicals.swing_structure,
                nearest_fibonacci_level=technicals.nearest_fibonacci_level,
                signal=technicals.signal,
                signal_reasons=technicals.signal_reasons,
                indicator=resolved_indicator,
                indicator_label=indicator_label,
                indicator_value=indicator_value,
            )
        )

    return _sort_rows(rows, resolved_indicator)
