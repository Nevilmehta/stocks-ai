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


def find_swing_points(
    highs: list[float], lows: list[float], pivot_strength: int = 3
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Classic swing high/low (fractal) detection: a bar is a swing high if it's
    the max within +/- pivot_strength neighbors, swing low if it's the min.
    Returns (swing_highs, swing_lows) as (index, value) pairs, oldest -> newest.
    Returns empty lists rather than raising when there isn't enough history."""
    n = len(highs)
    if n < 2 * pivot_strength + 1 or len(lows) != n:
        return [], []

    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []
    for i in range(pivot_strength, n - pivot_strength):
        high_window = highs[i - pivot_strength : i + pivot_strength + 1]
        if highs[i] == max(high_window):
            swing_highs.append((i, highs[i]))
        low_window = lows[i - pivot_strength : i + pivot_strength + 1]
        if lows[i] == min(low_window):
            swing_lows.append((i, lows[i]))

    return swing_highs, swing_lows


def classify_market_structure(
    swing_highs: list[tuple[int, float]], swing_lows: list[tuple[int, float]]
) -> str:
    """Compares the two most recent swing highs and two most recent swing lows
    to classify trend structure in plain "higher highs / lower lows" terms."""
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "Insufficient data"

    higher_high = swing_highs[-1][1] > swing_highs[-2][1]
    higher_low = swing_lows[-1][1] > swing_lows[-2][1]
    lower_high = swing_highs[-1][1] < swing_highs[-2][1]
    lower_low = swing_lows[-1][1] < swing_lows[-2][1]

    if higher_high and higher_low:
        return "Uptrend (higher highs & higher lows)"
    if lower_high and lower_low:
        return "Downtrend (lower highs & lower lows)"
    return "Sideways / Mixed"


FIBONACCI_RATIOS: list[float] = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]


def fibonacci_retracement_levels(swing_high: float, swing_low: float) -> dict[str, float]:
    """Standard retracement levels between a swing high and swing low. Returns
    an empty dict for degenerate/thin-data input (high <= low) rather than
    raising or returning misleading levels."""
    if swing_high <= swing_low:
        return {}

    span = swing_high - swing_low
    return {f"{ratio * 100:g}%": round(swing_high - span * ratio, 2) for ratio in FIBONACCI_RATIOS}


def nearest_fibonacci_level(
    price: float, levels: dict[str, float]
) -> tuple[str | None, float | None]:
    """Named level closest to `price`, plus the % distance from it."""
    if not levels or not price:
        return None, None
    name, value = min(levels.items(), key=lambda item: abs(item[1] - price))
    distance_percent = round(abs(value - price) / price * 100, 2)
    return name, distance_percent
