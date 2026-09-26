import uuid
from datetime import date

from app.providers.ai_provider import (
    StockContext,
    _parse_labeled_sections,
    _PromptRewritingAIProvider,
)
from app.schemas.stock import AIScore, AIScoreSubscores, StockDetail, TechnicalIndicators


class _FakeProvider(_PromptRewritingAIProvider):
    provider_name = "fake"

    def __init__(self, response: str | None = None, raise_error: bool = False):
        self._response = response
        self._raise_error = raise_error

    def _generate(self, prompt: str) -> str:
        if self._raise_error:
            raise RuntimeError("boom")
        return self._response or ""


def _make_context() -> StockContext:
    detail = StockDetail(
        id=uuid.uuid4(),
        symbol="TCS",
        name="Tata Consultancy Services Ltd",
        exchange="NSE",
        sector="Information Technology",
        industry="IT Services",
        description="",
        latest_price=2500.0,
        previous_close=2480.0,
        change=20.0,
        change_percent=0.8,
        as_of=date(2026, 1, 1),
        market_cap=1_000_000.0,
        pe_ratio=25.0,
        pb_ratio=8.0,
        roe=25.0,
        roce=30.0,
        eps=100.0,
        debt_to_equity=0.1,
        revenue_growth=10.0,
        profit_growth=8.0,
        week52_high=2700.0,
        week52_low=2000.0,
    )
    technicals = TechnicalIndicators(
        as_of=date(2026, 1, 1),
        sma_20=2400,
        sma_50=2350,
        sma_200=2200,
        ema_20=2400,
        ema_50=2350,
        ema_200=2200,
        rsi_14=55,
        macd=10,
        macd_signal=8,
        macd_histogram=2,
        bollinger_upper=2500,
        bollinger_middle=2400,
        bollinger_lower=2300,
        week52_high=2700,
        week52_low=2000,
        return_1m=2.0,
        return_3m=5.0,
        return_6m=10.0,
        return_1y=15.0,
        volatility=20.0,
        price_vs_sma50_percent=2.0,
        price_vs_sma200_percent=5.0,
        trend="Positive",
        momentum="Bullish",
    )
    score = AIScore(
        symbol="TCS",
        as_of=date(2026, 1, 1),
        overall_score=70,
        label="Strong",
        risk_label="Low",
        subscores=AIScoreSubscores(
            financial_strength=70, growth=70, profitability=70, valuation=70, technical_momentum=70, risk=70
        ),
        methodology_note="",
    )
    return StockContext(detail=detail, technicals=technicals, score=score)


def test_parse_labeled_sections_extracts_each_field():
    text = "[SUMMARY] A summary.\n[FINANCIAL_HEALTH] Healthy.\n[CONCLUSION] Balanced overall."
    sections = _parse_labeled_sections(text)
    assert sections["SUMMARY"] == "A summary."
    assert sections["FINANCIAL_HEALTH"] == "Healthy."
    assert sections["CONCLUSION"] == "Balanced overall."


def test_parse_labeled_sections_handles_missing_labels():
    assert _parse_labeled_sections("no labels here at all") == {}


def test_analyse_stock_uses_rewritten_sections_without_duplication():
    context = _make_context()
    response = (
        "[SUMMARY] TCS is a strong IT company.\n"
        "[FINANCIAL_HEALTH] Balance sheet is solid.\n"
        "[GROWTH] Growing steadily.\n"
        "[PROFITABILITY] Highly profitable.\n"
        "[VALUATION] Fairly valued.\n"
        "[TECHNICAL_PICTURE] Trending up.\n"
        "[CONCLUSION] Overall strong.\n"
    )
    provider = _FakeProvider(response=response)

    analysis = provider.analyse_stock(context)

    assert analysis.summary == "TCS is a strong IT company."
    assert analysis.financial_health == "Balance sheet is solid."
    assert analysis.growth == "Growing steadily."
    assert analysis.provider == "fake"
    # No section's text should bleed into another - each field is independent.
    assert "Balance sheet" not in analysis.summary
    assert "strong IT company" not in analysis.financial_health


def test_analyse_stock_falls_back_to_mock_draft_on_error():
    context = _make_context()
    provider = _FakeProvider(raise_error=True)

    analysis = provider.analyse_stock(context)

    assert analysis.provider == "mock"
    assert analysis.summary  # grounded mock text, not empty


def test_analyse_stock_falls_back_per_field_when_model_ignores_format():
    context = _make_context()
    provider = _FakeProvider(response="I cannot help with that.")

    analysis = provider.analyse_stock(context)

    # Nothing parsed -> every field stays the grounded mock draft, not garbage.
    assert "TCS" in analysis.summary
    assert analysis.provider == "fake"
