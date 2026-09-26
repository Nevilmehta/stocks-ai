"""Builds the TechnicalIndicators API response from raw price history rows.

Keeps the neutral-language classification (trend/momentum) here, separate
from the pure math in analytics/technicals.py.
"""

from __future__ import annotations

from app.analytics import technicals as ta
from app.models.price_history import PriceHistory
from app.schemas.stock import TechnicalIndicators
from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG, StrategyConfig


def _last(series: list[float | None]) -> float | None:
    return series[-1] if series else None


def compute_technical_indicators(
    rows: list[PriceHistory], config: StrategyConfig = DEFAULT_STRATEGY_CONFIG
) -> TechnicalIndicators:
    if not rows:
        return TechnicalIndicators(
            as_of=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            ema_20=None,
            ema_50=None,
            ema_200=None,
            rsi_14=None,
            macd=None,
            macd_signal=None,
            macd_histogram=None,
            bollinger_upper=None,
            bollinger_middle=None,
            bollinger_lower=None,
            week52_high=None,
            week52_low=None,
            return_1m=None,
            return_3m=None,
            return_6m=None,
            return_1y=None,
            volatility=None,
            price_vs_sma50_percent=None,
            price_vs_sma200_percent=None,
            trend="Data unavailable",
            momentum="Data unavailable",
        )

    closes = [float(r.close) for r in rows]
    highs = [float(r.high) for r in rows]
    lows = [float(r.low) for r in rows]
    latest_price = closes[-1]

    sma20 = _last(ta.sma_series(closes, config.sma_short))
    sma50 = _last(ta.sma_series(closes, config.sma_medium))
    sma200 = _last(ta.sma_series(closes, config.sma_long))
    ema20 = _last(ta.ema_series(closes, config.ema_short))
    ema50 = _last(ta.ema_series(closes, config.ema_medium))
    ema200 = _last(ta.ema_series(closes, config.ema_long))
    rsi14 = _last(ta.rsi_series(closes, config.rsi_period))

    macd_line, signal_line, histogram = ta.macd(closes, config.macd_fast, config.macd_slow, config.macd_signal)
    macd_latest = _last(macd_line)
    signal_latest = _last(signal_line)
    hist_latest = _last(histogram)

    upper, middle, lower = ta.bollinger_bands(closes, config.bollinger_period, config.bollinger_num_std)

    week52_high, week52_low = ta.fifty_two_week_high_low(highs, lows)

    return_1m = ta.period_return(closes, ta.TRADING_DAYS_PER_MONTH)
    return_3m = ta.period_return(closes, ta.TRADING_DAYS_PER_MONTH * 3)
    return_6m = ta.period_return(closes, ta.TRADING_DAYS_PER_MONTH * 6)
    return_1y = ta.period_return(closes, ta.TRADING_DAYS_PER_YEAR)
    volatility = ta.annualized_volatility(closes)

    price_vs_sma50 = ((latest_price - sma50) / sma50 * 100) if sma50 else None
    price_vs_sma200 = ((latest_price - sma200) / sma200 * 100) if sma200 else None

    trend = _classify_trend(price_vs_sma50, price_vs_sma200)
    momentum = _classify_momentum(rsi14, macd_latest, signal_latest)

    return TechnicalIndicators(
        as_of=rows[-1].date,
        sma_20=_round(sma20),
        sma_50=_round(sma50),
        sma_200=_round(sma200),
        ema_20=_round(ema20),
        ema_50=_round(ema50),
        ema_200=_round(ema200),
        rsi_14=_round(rsi14),
        macd=_round(macd_latest),
        macd_signal=_round(signal_latest),
        macd_histogram=_round(hist_latest),
        bollinger_upper=_round(_last(upper)),
        bollinger_middle=_round(_last(middle)),
        bollinger_lower=_round(_last(lower)),
        week52_high=_round(week52_high),
        week52_low=_round(week52_low),
        return_1m=_round(return_1m),
        return_3m=_round(return_3m),
        return_6m=_round(return_6m),
        return_1y=_round(return_1y),
        volatility=_round(volatility),
        price_vs_sma50_percent=_round(price_vs_sma50),
        price_vs_sma200_percent=_round(price_vs_sma200),
        trend=trend,
        momentum=momentum,
    )


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def _classify_trend(price_vs_sma50: float | None, price_vs_sma200: float | None) -> str:
    if price_vs_sma50 is None or price_vs_sma200 is None:
        return "Data unavailable"
    if price_vs_sma50 > 1 and price_vs_sma200 > 1:
        return "Positive"
    if price_vs_sma50 < -1 and price_vs_sma200 < -1:
        return "Negative"
    return "Neutral"


def _classify_momentum(
    rsi: float | None, macd_value: float | None, signal_value: float | None
) -> str:
    if rsi is None or macd_value is None or signal_value is None:
        return "Data unavailable"

    macd_positive = macd_value > signal_value
    if rsi >= 60 and macd_positive:
        return "Positive"
    if rsi <= 40 and not macd_positive:
        return "Negative"
    return "Neutral"
