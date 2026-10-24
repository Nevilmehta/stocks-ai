import math

from app.analytics.technicals import (
    annualized_volatility,
    bollinger_bands,
    classify_market_structure,
    ema_series,
    fibonacci_retracement_levels,
    fifty_two_week_high_low,
    find_swing_points,
    macd,
    nearest_fibonacci_level,
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


def test_find_swing_points_returns_empty_for_thin_history():
    highs = [100.0, 101.0, 102.0]
    lows = [95.0, 96.0, 97.0]
    swing_highs, swing_lows = find_swing_points(highs, lows, pivot_strength=3)
    assert swing_highs == []
    assert swing_lows == []


def test_find_swing_points_detects_a_clean_peak_and_trough():
    # Rises to a peak at index 5, then falls to a trough at index 10, then rises again.
    highs = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 101, 102, 103]
    lows = [h - 5 for h in highs]
    swing_highs, swing_lows = find_swing_points(highs, lows, pivot_strength=3)
    assert (5, 105) in swing_highs
    assert (10, 95) in swing_lows


def test_classify_market_structure_detects_uptrend():
    swing_highs = [(2, 100.0), (8, 110.0)]
    swing_lows = [(5, 90.0), (11, 95.0)]
    assert classify_market_structure(swing_highs, swing_lows) == "Uptrend (higher highs & higher lows)"


def test_classify_market_structure_detects_downtrend():
    swing_highs = [(2, 110.0), (8, 100.0)]
    swing_lows = [(5, 95.0), (11, 90.0)]
    assert classify_market_structure(swing_highs, swing_lows) == "Downtrend (lower highs & lower lows)"


def test_classify_market_structure_insufficient_data():
    assert classify_market_structure([], []) == "Insufficient data"
    assert classify_market_structure([(1, 100.0)], [(2, 90.0)]) == "Insufficient data"


def test_fibonacci_retracement_levels_span_high_to_low():
    levels = fibonacci_retracement_levels(swing_high=200.0, swing_low=100.0)
    assert levels["0%"] == 200.0
    assert levels["100%"] == 100.0
    assert levels["50%"] == 150.0
    assert levels["61.8%"] == round(200.0 - 100.0 * 0.618, 2)


def test_fibonacci_retracement_levels_empty_for_degenerate_input():
    assert fibonacci_retracement_levels(swing_high=100.0, swing_low=100.0) == {}
    assert fibonacci_retracement_levels(swing_high=90.0, swing_low=100.0) == {}


def test_nearest_fibonacci_level_picks_closest():
    levels = {"0%": 200.0, "50%": 150.0, "100%": 100.0}
    name, distance = nearest_fibonacci_level(148.0, levels)
    assert name == "50%"
    assert distance == round(2.0 / 148.0 * 100, 2)


def test_nearest_fibonacci_level_empty_levels():
    assert nearest_fibonacci_level(100.0, {}) == (None, None)
