from app.analytics.scoring import (
    calculate_financial_strength,
    calculate_growth,
    calculate_profitability,
    calculate_risk_safety,
    calculate_technical_momentum,
    calculate_valuation,
    compute_ai_score,
    normalize,
    normalize_inverse,
    overall_label,
    risk_label_from_safety_score,
)
from app.schemas.stock import FinancialPeriod, TechnicalIndicators


def _financial_period(**overrides) -> FinancialPeriod:
    defaults = dict(
        period_type="annual",
        period_label="FY2026",
        fiscal_year=2026,
        revenue=10000.0,
        net_profit=1500.0,
        operating_profit=2000.0,
        eps=20.0,
        operating_cash_flow=1600.0,
        total_debt=5000.0,
        pe_ratio=20.0,
        pb_ratio=3.0,
        roe=18.0,
        roce=20.0,
        debt_to_equity=0.8,
        revenue_growth=12.0,
        profit_growth=15.0,
        net_margin=15.0,
        market_cap=100000.0,
    )
    defaults.update(overrides)
    return FinancialPeriod(**defaults)


def _technicals(**overrides) -> TechnicalIndicators:
    defaults = dict(
        as_of="2026-09-22",
        sma_20=100.0,
        sma_50=100.0,
        sma_200=100.0,
        ema_20=100.0,
        ema_50=100.0,
        ema_200=100.0,
        rsi_14=55.0,
        macd=1.0,
        macd_signal=0.5,
        macd_histogram=0.5,
        bollinger_upper=110.0,
        bollinger_middle=100.0,
        bollinger_lower=90.0,
        week52_high=120.0,
        week52_low=80.0,
        return_1m=2.0,
        return_3m=5.0,
        return_6m=8.0,
        return_1y=12.0,
        volatility=25.0,
        price_vs_sma50_percent=2.0,
        price_vs_sma200_percent=5.0,
        trend="Positive",
        momentum="Positive",
    )
    defaults.update(overrides)
    return TechnicalIndicators(**defaults)


def test_normalize_clamps_and_handles_none():
    assert normalize(5, 0, 10) == 50.0
    assert normalize(-100, 0, 10) == 0.0
    assert normalize(1000, 0, 10) == 100.0
    assert normalize(None, 0, 10) == 50.0


def test_normalize_inverse_flips_direction():
    assert normalize_inverse(0, 0, 10) == 100.0
    assert normalize_inverse(10, 0, 10) == 0.0


def test_financial_strength_rewards_low_debt_and_strong_cash_flow():
    strong = _financial_period(debt_to_equity=0.2, operating_cash_flow=1.4 * 1500)
    weak = _financial_period(debt_to_equity=2.4, operating_cash_flow=0.3 * 1500)
    assert calculate_financial_strength(strong) > calculate_financial_strength(weak)


def test_growth_rewards_positive_growth():
    strong = _financial_period(revenue_growth=22, profit_growth=30)
    weak = _financial_period(revenue_growth=-3, profit_growth=-8)
    prior = _financial_period(eps=15.0, fiscal_year=2025, period_label="FY2025")
    assert calculate_growth(strong, [prior, strong]) > calculate_growth(weak, [prior, weak])


def test_profitability_rewards_high_returns_and_margins():
    strong = _financial_period(roe=28, roce=26, net_margin=22, operating_profit=2800)
    weak = _financial_period(roe=6, roce=7, net_margin=4, operating_profit=1000)
    assert calculate_profitability(strong) > calculate_profitability(weak)


def test_valuation_rewards_cheaper_than_peers():
    peers = [_financial_period(pe_ratio=30, pb_ratio=5) for _ in range(3)]
    cheap = _financial_period(pe_ratio=15, pb_ratio=2)
    expensive = _financial_period(pe_ratio=55, pb_ratio=9)
    assert calculate_valuation(cheap, peers) > calculate_valuation(expensive, peers)


def test_technical_momentum_rewards_uptrend():
    positive = _technicals(price_vs_sma50_percent=8, price_vs_sma200_percent=12, rsi_14=65, macd_histogram=1.5)
    negative = _technicals(price_vs_sma50_percent=-8, price_vs_sma200_percent=-12, rsi_14=35, macd_histogram=-1.5)
    assert calculate_technical_momentum(positive) > calculate_technical_momentum(negative)


def test_risk_safety_rewards_low_volatility_and_low_debt():
    safe_period = _financial_period(debt_to_equity=0.2)
    risky_period = _financial_period(debt_to_equity=2.3)
    safe_tech = _technicals(volatility=16)
    risky_tech = _technicals(volatility=44)
    consistent = [_financial_period(profit_growth=10.0), _financial_period(profit_growth=11.0)]
    assert calculate_risk_safety(safe_tech, safe_period, consistent) > calculate_risk_safety(
        risky_tech, risky_period, consistent
    )


def test_risk_label_thresholds():
    assert risk_label_from_safety_score(80) == "Low"
    assert risk_label_from_safety_score(50) == "Moderate"
    assert risk_label_from_safety_score(20) == "High"


def test_overall_label_thresholds():
    assert overall_label(90) == "Very Strong"
    assert overall_label(75) == "Strong"
    assert overall_label(60) == "Balanced"
    assert overall_label(35) == "Weak"
    assert overall_label(10) == "Very Weak"


def test_compute_ai_score_returns_none_without_financials():
    result = compute_ai_score([], _technicals(), [])
    assert result is None


def test_compute_ai_score_end_to_end_is_bounded_and_consistent():
    periods = [_financial_period(fiscal_year=year, period_label=f"FY{year}") for year in range(2022, 2027)]
    result = compute_ai_score(periods, _technicals(), [])

    assert result is not None
    assert 0 <= result.overall_score <= 100
    assert result.label == overall_label(result.overall_score)
    assert result.risk_label == risk_label_from_safety_score(result.risk)
    for subscore in (
        result.financial_strength,
        result.growth,
        result.profitability,
        result.valuation,
        result.technical_momentum,
        result.risk,
    ):
        assert 0 <= subscore <= 100


def test_compute_ai_score_strong_company_scores_higher_than_weak_company():
    strong_periods = [
        _financial_period(
            fiscal_year=year,
            period_label=f"FY{year}",
            revenue_growth=18,
            profit_growth=22,
            roe=26,
            roce=24,
            net_margin=20,
            debt_to_equity=0.3,
            pe_ratio=18,
            pb_ratio=2.5,
        )
        for year in range(2022, 2027)
    ]
    weak_periods = [
        _financial_period(
            fiscal_year=year,
            period_label=f"FY{year}",
            revenue_growth=-2,
            profit_growth=-10,
            roe=5,
            roce=6,
            net_margin=3,
            debt_to_equity=2.4,
            pe_ratio=60,
            pb_ratio=9,
        )
        for year in range(2022, 2027)
    ]

    strong_result = compute_ai_score(strong_periods, _technicals(volatility=16), [])
    weak_result = compute_ai_score(weak_periods, _technicals(volatility=44), [])

    assert strong_result is not None and weak_result is not None
    assert strong_result.overall_score > weak_result.overall_score
