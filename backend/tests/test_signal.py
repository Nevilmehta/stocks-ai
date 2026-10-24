from datetime import date, timedelta

from app.analytics.signal import derive_trade_signal, historical_oversold_forward_return
from app.models.price_history import PriceHistory
from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG


def _rows(closes: list[float]) -> list[PriceHistory]:
    start = date.today() - timedelta(days=len(closes))
    return [
        PriceHistory(date=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1_000_000)
        for i, c in enumerate(closes)
    ]


def test_derive_trade_signal_buy_when_all_factors_align():
    result = derive_trade_signal(
        rsi_14=25.0,  # oversold -> bullish
        price_vs_sma50_percent=5.0,
        price_vs_sma200_percent=3.0,  # both positive -> bullish
        swing_structure="Uptrend (higher highs & higher lows)",  # bullish
        config=DEFAULT_STRATEGY_CONFIG,
    )
    assert result.signal == "buy"
    assert len(result.reasons) == 3


def test_derive_trade_signal_sell_when_all_factors_align():
    result = derive_trade_signal(
        rsi_14=80.0,  # overbought -> bearish
        price_vs_sma50_percent=-4.0,
        price_vs_sma200_percent=-6.0,  # both negative -> bearish
        swing_structure="Downtrend (lower highs & lower lows)",  # bearish
        config=DEFAULT_STRATEGY_CONFIG,
    )
    assert result.signal == "sell"
    assert len(result.reasons) == 3


def test_derive_trade_signal_neutral_when_factors_conflict():
    result = derive_trade_signal(
        rsi_14=50.0,
        price_vs_sma50_percent=1.0,
        price_vs_sma200_percent=-1.0,
        swing_structure="Sideways / Mixed",
        config=DEFAULT_STRATEGY_CONFIG,
    )
    assert result.signal == "neutral"


def test_derive_trade_signal_neutral_when_data_missing():
    result = derive_trade_signal(
        rsi_14=None,
        price_vs_sma50_percent=None,
        price_vs_sma200_percent=None,
        swing_structure="Data unavailable",
        config=DEFAULT_STRATEGY_CONFIG,
    )
    assert result.signal == "neutral"
    assert result.reasons == ["Indicators are mixed or insufficient for a clear signal"]


def test_historical_oversold_forward_return_none_for_short_history():
    closes = [100.0 + i for i in range(20)]
    assert historical_oversold_forward_return(_rows(closes), DEFAULT_STRATEGY_CONFIG) is None


def test_historical_oversold_forward_return_averages_bounce_back_occurrences():
    # Four short, sharp dip-then-recover cycles with a flat buffer between
    # each, so RSI resets to neutral before the next dip and each one
    # registers as a single, brief oversold occurrence followed by a clear
    # bounce - the forward 30-day return from each dip should be positive.
    closes: list[float] = [100.0] * 20
    for _ in range(4):
        last = closes[-1]
        for _day in range(2):
            last *= 0.90
            closes.append(last)
        for _day in range(35):
            last *= 1.02
            closes.append(last)
        closes += [last] * 15

    result = historical_oversold_forward_return(_rows(closes), DEFAULT_STRATEGY_CONFIG)
    assert result is not None
    assert result["occurrences"] >= 3
    assert result["avg_forward_return_30d"] > 0
