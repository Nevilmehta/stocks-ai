"""Pure technical-indicator calculations over OHLCV series.

Every function takes plain lists (oldest -> newest) and returns plain lists
or floats - no DB or provider dependency, so these are cheap to unit test
and safe to reuse from the scoring engine later.
"""

from __future__ import annotations

import math

TRADING_DAYS_PER_MONTH = 21
TRADING_DAYS_PER_YEAR = 252


def sma_series(values: list[float], period: int) -> list[float | None]:
    """Simple moving average. First `period - 1` entries are None (warmup)."""
    if period <= 0:
        raise ValueError("period must be positive")

    result: list[float | None] = [None] * len(values)
    running_sum = 0.0
    for i, value in enumerate(values):
        running_sum += value
        if i >= period:
            running_sum -= values[i - period]
        if i >= period - 1:
            result[i] = running_sum / period
    return result


def ema_series(values: list[float], period: int) -> list[float | None]:
    """Exponential moving average, seeded with the SMA of the first `period` values."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return [None] * len(values)

    multiplier = 2 / (period + 1)
    result: list[float | None] = [None] * len(values)

    seed = sum(values[:period]) / period
    result[period - 1] = seed
    prev = seed

    for i in range(period, len(values)):
        current = (values[i] - prev) * multiplier + prev
        result[i] = current
        prev = current

    return result


def rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder's RSI. Bounded 0-100; first `period` entries are None."""
    n = len(closes)
    result: list[float | None] = [None] * n
    if n <= period:
        return result

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta

    avg_gain = gains / period
    avg_loss = losses / period
    result[period] = _rsi_from_averages(avg_gain, avg_loss)

    for i in range(period + 1, n):
        delta = closes[i] - closes[i - 1]
        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[i] = _rsi_from_averages(avg_gain, avg_loss)

    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Returns (macd_line, signal_line, histogram)."""
    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)

    macd_line: list[float | None] = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]

    # Signal line is the EMA of the MACD line, computed only over its defined values.
    defined_start = next((i for i, v in enumerate(macd_line) if v is not None), None)
    if defined_start is None:
        return macd_line, [None] * len(closes), [None] * len(closes)

    defined_values = [v for v in macd_line[defined_start:] if v is not None]
    signal_defined = ema_series(defined_values, signal)

    signal_line: list[float | None] = [None] * len(closes)
    for offset, value in enumerate(signal_defined):
        signal_line[defined_start + offset] = value

    histogram: list[float | None] = [
        (m - s) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]

    return macd_line, signal_line, histogram


def bollinger_bands(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Returns (upper, middle, lower) bands."""
    middle = sma_series(closes, period)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)

    for i in range(len(closes)):
        if middle[i] is None:
            continue
        window = closes[i - period + 1 : i + 1]
        mean = middle[i]
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std

    return upper, middle, lower


def period_return(closes: list[float], trading_days: int) -> float | None:
    """Percentage return over the last `trading_days`, or None if not enough history."""
    if len(closes) <= trading_days:
        return None
    latest = closes[-1]
    past = closes[-1 - trading_days]
    if past == 0:
        return None
    return ((latest - past) / past) * 100


def annualized_volatility(closes: list[float], window: int = TRADING_DAYS_PER_YEAR) -> float | None:
    """Annualized volatility (%) from daily log returns over the trailing `window` days."""
    if len(closes) < 2:
        return None
    recent = closes[-(window + 1) :] if len(closes) > window else closes
    returns = [
        math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent)) if recent[i - 1] > 0
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    daily_std = math.sqrt(variance)
    return daily_std * math.sqrt(window) * 100


def fifty_two_week_high_low(
    highs: list[float], lows: list[float], window: int = TRADING_DAYS_PER_YEAR
) -> tuple[float | None, float | None]:
    recent_highs = highs[-window:] if len(highs) > window else highs
    recent_lows = lows[-window:] if len(lows) > window else lows
    if not recent_highs or not recent_lows:
        return None, None
    return max(recent_highs), min(recent_lows)
