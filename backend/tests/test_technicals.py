import math

from app.analytics.technicals import (
    annualized_volatility,
    bollinger_bands,
    ema_series,
    fifty_two_week_high_low,
    macd,
    period_return,
    rsi_series,
    sma_series,
)


def test_sma_basic():
    values = [1, 2, 3, 4, 5, 6]
    result = sma_series(values, 3)
    assert result[:2] == [None, None]
    assert result[2] == 2  # (1+2+3)/3
    assert result[3] == 3  # (2+3+4)/3
    assert result[-1] == 5  # (4+5+6)/3


def test_sma_constant_series_equals_the_constant():
    values = [10.0] * 30
    result = sma_series(values, 20)
    assert result[19] == 10.0
    assert result[-1] == 10.0


def test_ema_seeds_with_sma_then_diverges():
    values = [1, 2, 3, 4, 5, 6, 7, 8]
    result = ema_series(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == sum(values[:3]) / 3
    assert result[-1] is not None


def test_rsi_all_gains_is_100():
    closes = [float(i) for i in range(1, 30)]  # strictly increasing
    result = rsi_series(closes, period=14)
    assert result[14] == 100.0
    assert result[-1] == 100.0


def test_rsi_all_losses_is_0():
    closes = [float(i) for i in range(30, 1, -1)]  # strictly decreasing
    result = rsi_series(closes, period=14)
    assert result[14] == 0.0
    assert result[-1] == 0.0


def test_rsi_is_bounded():
    closes = [100 + 5 * math.sin(i / 3) for i in range(60)]
    result = rsi_series(closes, period=14)
    for value in result:
        if value is not None:
            assert 0 <= value <= 100


def test_macd_is_zero_for_constant_prices():
    closes = [50.0] * 60
    macd_line, signal_line, histogram = macd(closes)
    assert macd_line[-1] == 0.0
    assert signal_line[-1] == 0.0
    assert histogram[-1] == 0.0


def test_bollinger_bands_collapse_for_constant_prices():
    closes = [25.0] * 30
    upper, middle, lower = bollinger_bands(closes, period=20)
    assert upper[-1] == 25.0
    assert middle[-1] == 25.0
    assert lower[-1] == 25.0


def test_bollinger_upper_above_lower_for_varying_prices():
    closes = [100 + (i % 5) for i in range(30)]
    upper, _, lower = bollinger_bands(closes, period=20)
    assert upper[-1] > lower[-1]


def test_period_return_positive_for_rising_prices():
    closes = [100.0 + i for i in range(30)]
    result = period_return(closes, trading_days=10)
    assert result is not None
    assert result > 0


def test_period_return_none_when_insufficient_history():
    closes = [100.0, 101.0]
    assert period_return(closes, trading_days=10) is None


def test_annualized_volatility_zero_for_constant_prices():
    closes = [100.0] * 300
    result = annualized_volatility(closes)
    assert result == 0.0


def test_annualized_volatility_positive_for_varying_prices():
    closes = [100 + ((-1) ** i) * 2 for i in range(300)]
    result = annualized_volatility(closes)
    assert result is not None
    assert result > 0


def test_fifty_two_week_high_low():
    highs = [100.0 + i for i in range(300)]
    lows = [90.0 + i for i in range(300)]
    high, low = fifty_two_week_high_low(highs, lows)
    assert high == max(highs[-252:])
    assert low == min(lows[-252:])
