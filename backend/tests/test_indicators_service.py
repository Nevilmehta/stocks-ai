from datetime import date, timedelta

from app.analytics.indicators_service import compute_technical_indicators
from app.models.price_history import PriceHistory


def _make_rows(closes: list[float]) -> list[PriceHistory]:
    start = date.today() - timedelta(days=len(closes) * 2)
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            PriceHistory(
                date=start + timedelta(days=i),
                open=close,
                high=close * 1.01,
                low=close * 0.99,
                close=close,
                volume=1_000_000,
            )
        )
    return rows


def test_empty_history_returns_data_unavailable():
    result = compute_technical_indicators([])
    assert result.trend == "Data unavailable"
    assert result.momentum == "Data unavailable"
    assert result.sma_20 is None
    assert result.swing_structure == "Data unavailable"
    assert result.signal == "neutral"
    assert result.fibonacci_levels is None
    assert result.price_vs_ema50_percent is None
    assert result.price_vs_ema200_percent is None


def test_strong_uptrend_is_classified_positive():
    closes = [100 + i * 1.5 for i in range(300)]
    result = compute_technical_indicators(_make_rows(closes))

    assert result.trend == "Positive"
    assert result.price_vs_sma50_percent is not None
    assert result.price_vs_sma50_percent > 0
    assert result.return_1y is not None
    assert result.return_1y > 0
    assert result.rsi_14 is not None
    assert 0 <= result.rsi_14 <= 100
    # A pure monotonic rise pins RSI at 100 (overbought - a bearish factor on
    # its own) while leaving no swing points, so the signal itself isn't
    # asserted here; derive_trade_signal's own factor logic is tested
    # directly with controlled inputs in test_signal.py.
    assert result.signal in {"buy", "sell", "neutral"}
    assert result.signal_reasons
    assert result.fibonacci_levels is not None
    assert result.nearest_fibonacci_level is not None
    assert result.price_vs_ema50_percent is not None
    assert result.price_vs_ema50_percent > 0


def test_strong_downtrend_is_classified_negative():
    closes = [500 - i * 1.2 for i in range(300)]
    result = compute_technical_indicators(_make_rows(closes))

    assert result.trend == "Negative"
    assert result.price_vs_sma200_percent is not None
    assert result.price_vs_sma200_percent < 0
    assert result.signal in {"buy", "sell", "neutral"}
    assert result.price_vs_ema200_percent is not None
    assert result.price_vs_ema200_percent < 0


def test_week52_high_low_present_for_long_history():
    closes = [100 + (i % 50) for i in range(300)]
    result = compute_technical_indicators(_make_rows(closes))

    assert result.week52_high is not None
    assert result.week52_low is not None
    assert result.week52_high >= result.week52_low
