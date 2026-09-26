"""Regression guard: StrategyConfig's defaults must exactly match the values
that were hardcoded before this feature existed, so that "no strategy has
been activated yet" behaves identically to the original app. If one of these
assertions ever needs to change, it means today's actual computed behavior is
about to change for every user with no strategy activated - that should be a
deliberate, reviewed decision, not an accident.
"""

from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG, StrategyConfig


def test_defaults_match_original_hardcoded_indicator_periods():
    c = DEFAULT_STRATEGY_CONFIG
    assert (c.sma_short, c.sma_medium, c.sma_long) == (20, 50, 200)
    assert (c.ema_short, c.ema_medium, c.ema_long) == (20, 50, 200)
    assert c.rsi_period == 14
    assert (c.macd_fast, c.macd_slow, c.macd_signal) == (12, 26, 9)
    assert (c.bollinger_period, c.bollinger_num_std) == (20, 2.0)


def test_defaults_match_original_hardcoded_score_weights():
    c = DEFAULT_STRATEGY_CONFIG
    assert c.weight_financial_strength == 0.25
    assert c.weight_growth == 0.20
    assert c.weight_profitability == 0.20
    assert c.weight_valuation == 0.15
    assert c.weight_technical_momentum == 0.10
    assert c.weight_risk == 0.10
    assert abs(
        c.weight_financial_strength
        + c.weight_growth
        + c.weight_profitability
        + c.weight_valuation
        + c.weight_technical_momentum
        + c.weight_risk
        - 1.0
    ) < 1e-9


def test_defaults_match_original_hardcoded_thresholds():
    c = DEFAULT_STRATEGY_CONFIG
    assert (c.debt_to_equity_good, c.debt_to_equity_bad) == (0.0, 2.5)
    assert (c.roe_low, c.roe_high) == (5.0, 30.0)
    assert (c.roce_low, c.roce_high) == (5.0, 30.0)
    assert (c.pe_fallback_low, c.pe_fallback_high) == (10.0, 45.0)
    assert (c.rsi_oversold, c.rsi_overbought) == (30.0, 70.0)
    assert (c.risk_moderate_cutoff, c.risk_low_cutoff) == (40.0, 70.0)
    assert (c.overall_weak_cutoff, c.overall_balanced_cutoff, c.overall_strong_cutoff, c.overall_very_strong_cutoff) == (
        30.0,
        50.0,
        70.0,
        85.0,
    )


def test_weights_must_sum_to_one():
    import pytest

    with pytest.raises(ValueError):
        StrategyConfig(weight_financial_strength=0.9)
