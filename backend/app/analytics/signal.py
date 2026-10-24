"""Deterministic buy/sell/neutral signal derivation, built entirely from the
same indicator values already computed in indicators_service.py - no AI model
involved. Every contributing factor is returned as a plain-language reason so
the signal is always shown with its "why," never as an opaque directive.

This module is a separate, intentional carve-out from app/providers/
ai_provider.py's "never say Buy/Sell" rule, which is scoped to AI-generated
free text (Research GPT, stock analysis panel). The signal here is rendered
on the frontend as a labeled mechanical rule output, paired with a disclaimer
that it is not personalized investment advice and not AI-generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.analytics import technicals as ta
from app.models.price_history import PriceHistory
from app.schemas.strategy import StrategyConfig

Signal = Literal["buy", "sell", "neutral"]

_MIN_OVERSOLD_OCCURRENCES = 3
_FORWARD_WINDOW_DAYS = 30


@dataclass
class TradeSignalResult:
    signal: Signal
    reasons: list[str] = field(default_factory=list)


def derive_trade_signal(
    rsi_14: float | None,
    price_vs_sma50_percent: float | None,
    price_vs_sma200_percent: float | None,
    swing_structure: str,
    config: StrategyConfig,
) -> TradeSignalResult:
    """Three independent factors, each contributing +1 (bullish), -1 (bearish)
    or 0 (neutral/unavailable) to a simple tally: RSI oversold/overbought,
    price trend vs SMA50/SMA200, and swing (higher-high/lower-low) structure.
    Net >= 2 -> "buy", net <= -2 -> "sell", otherwise "neutral". Fibonacci
    proximity is deliberately NOT included here - there's no non-arbitrary
    "near a level" threshold, and folding a fuzzy factor into this tally would
    turn an inspectable rule into one with a hidden magic number."""
    score = 0
    reasons: list[str] = []

    if rsi_14 is not None:
        if rsi_14 < config.rsi_oversold:
            score += 1
            reasons.append(f"RSI {rsi_14:.1f} is oversold (< {config.rsi_oversold:g})")
        elif rsi_14 > config.rsi_overbought:
            score -= 1
            reasons.append(f"RSI {rsi_14:.1f} is overbought (> {config.rsi_overbought:g})")

    if price_vs_sma50_percent is not None and price_vs_sma200_percent is not None:
        if price_vs_sma50_percent > 0 and price_vs_sma200_percent > 0:
            score += 1
            reasons.append("Price is above both the 50- and 200-period moving averages")
        elif price_vs_sma50_percent < 0 and price_vs_sma200_percent < 0:
            score -= 1
            reasons.append("Price is below both the 50- and 200-period moving averages")

    if "Uptrend" in swing_structure:
        score += 1
        reasons.append("Swing structure shows higher highs & higher lows")
    elif "Downtrend" in swing_structure:
        score -= 1
        reasons.append("Swing structure shows lower highs & lower lows")

    if score >= 2:
        signal: Signal = "buy"
    elif score <= -2:
        signal = "sell"
    else:
        signal = "neutral"
        if not reasons:
            reasons.append("Indicators are mixed or insufficient for a clear signal")

    return TradeSignalResult(signal=signal, reasons=reasons)


def historical_oversold_forward_return(
    rows: list[PriceHistory], config: StrategyConfig
) -> dict | None:
    """Backward-looking fact, not a forward prediction: scans this stock's own
    price history for every past occurrence of RSI dropping into oversold
    territory, and averages the actual return over the following 30 trading
    days. Consecutive oversold days are treated as a single occurrence (only
    the first day of each oversold streak counts), so a stock that stays
    oversold for a week isn't counted 5 times for one event. Returns None if
    there are fewer than 3 qualifying occurrences in the available history."""
    closes = [float(r.close) for r in rows]
    if len(closes) < config.rsi_period + _FORWARD_WINDOW_DAYS + 1:
        return None

    rsi_values = ta.rsi_series(closes, config.rsi_period)

    forward_returns: list[float] = []
    for i, rsi in enumerate(rsi_values):
        if rsi is None or rsi >= config.rsi_oversold:
            continue
        previous = rsi_values[i - 1] if i > 0 else None
        if previous is not None and previous < config.rsi_oversold:
            continue  # mid-streak, not the start of a new oversold occurrence
        if i + _FORWARD_WINDOW_DAYS >= len(closes):
            continue
        entry_price = closes[i]
        if not entry_price:
            continue
        forward_price = closes[i + _FORWARD_WINDOW_DAYS]
        forward_returns.append((forward_price - entry_price) / entry_price * 100)

    if len(forward_returns) < _MIN_OVERSOLD_OCCURRENCES:
        return None

    return {
        "occurrences": len(forward_returns),
        "avg_forward_return_30d": round(sum(forward_returns) / len(forward_returns), 2),
    }
