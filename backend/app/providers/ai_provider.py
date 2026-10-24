"""AI provider abstraction.

An AIProvider only ever EXPLAINS numbers that have already been computed
elsewhere (analytics/technicals.py, analytics/scoring.py) - it never invents
market data or calculates scores itself. This is the hallucination-protection
boundary: every figure quoted in generated text traces back to a field on
`StockContext`, which is built from the same data the frontend displays.

Also: no output here ever says "Buy", "Sell", "Strong Buy" or gives a target
price - only neutral research framing (see DISCLAIMER below).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.schemas.research import AIAnalysis
from app.schemas.stock import AIScore, StockDetail, TechnicalIndicators

DISCLAIMER = (
    "This is AI-assisted research generated from the metrics shown on this page. "
    "It is for informational and educational purposes only, not personalized "
    "investment advice. Verify independently before making financial decisions."
)


@dataclass
class StockContext:
    detail: StockDetail
    technicals: TechnicalIndicators
    score: AIScore | None
    strategy_name: str = "Default"


@dataclass
class MarketOverviewContext:
    """Grounding for questions with no specific company mentioned - "top
    stocks today", "what's moving", "when was this last updated". Built from
    the same MarketDataProvider.get_market_overview() the dashboard uses, so
    the numbers always match what's on screen."""

    as_of: date | None
    total_companies: int
    advancers: int
    decliners: int
    top_gainers: list[dict]
    top_losers: list[dict]
    strategy_name: str = "Default"


@dataclass
class HistoricalPriceContext:
    """Grounding for "what was X's price on <date>" questions - a specific
    past trading day's real OHLCV, not the latest snapshot StockContext
    carries. See app/services/historical_price_lookup.py for how this gets
    built (date parsing + the nearest-prior-trading-day fallback)."""

    symbol: str
    name: str
    requested_date: date
    resolved_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int

    @property
    def date_was_adjusted(self) -> bool:
        return self.resolved_date != self.requested_date


class AIProvider(ABC):
    @abstractmethod
    def analyse_stock(self, context: StockContext) -> AIAnalysis: ...

    @abstractmethod
    def compare_stocks(self, contexts: list[StockContext]) -> str: ...

    @abstractmethod
    def answer_question(self, question: str, contexts: list[StockContext]) -> str: ...

    @abstractmethod
    def answer_market_question(self, question: str, overview: MarketOverviewContext) -> str: ...

    @abstractmethod
    def answer_historical_price_question(self, question: str, context: HistoricalPriceContext) -> str: ...


def _fmt_pct(value: float | None) -> str:
    return f"{value:+.1f}%" if value is not None else "unavailable"


def _fmt_num(value: float | None, digits: int = 2) -> str:
    return f"{value:.{digits}f}" if value is not None else "unavailable"


def _parse_labeled_sections(text: str) -> dict[str, str]:
    """Parses "[LABEL] text..." lines back into a dict, where a section's text
    runs until the next [LABEL] or the end of the string. Missing/malformed
    labels just don't appear in the result - callers fall back to the
    grounded draft per-field, so a model that ignores the format entirely
    degrades safely to "no change" rather than producing garbage."""
    pattern = re.compile(r"\[([A-Z_]+)\]\s*")
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip()
    return sections


def _tier(value: float | None, low: float, high: float) -> str:
    if value is None:
        return "unavailable"
    if value >= high:
        return "strong"
    if value >= low:
        return "moderate"
    return "weak"


class MockAIProvider(AIProvider):
    """Deterministic, template-based research text built entirely from the
    structured numbers on `StockContext`. No randomness, no external calls -
    the same input always produces the same output."""

    def analyse_stock(self, context: StockContext) -> AIAnalysis:
        d, t, s = context.detail, context.technicals, context.score

        summary = self._summary(context)
        financial_health = self._financial_health(context)
        growth = self._growth(context)
        profitability = self._profitability(context)
        valuation = self._valuation(context)
        technical_picture = self._technical_picture(context)
        strengths, risks = self._strengths_and_risks(context)
        things_to_monitor = self._things_to_monitor(context)
        conclusion = self._conclusion(context)

        return AIAnalysis(
            symbol=d.symbol,
            generated_at=datetime.now(timezone.utc),
            provider="mock",
            summary=summary,
            financial_health=financial_health,
            growth=growth,
            profitability=profitability,
            valuation=valuation,
            technical_picture=technical_picture,
            strengths=strengths,
            risks=risks,
            things_to_monitor=things_to_monitor,
            conclusion=conclusion,
            disclaimer=DISCLAIMER,
        )

    def compare_stocks(self, contexts: list[StockContext]) -> str:
        if len(contexts) < 2:
            return "Mention at least two companies to compare, e.g. \"Compare TCS and Infosys\"."

        lines = [f"Comparing {', '.join(c.detail.symbol for c in contexts)}:", ""]

        for ctx in contexts:
            d, s = ctx.detail, ctx.score
            score_part = f"AI Research Score {s.overall_score}/100 ({s.label})" if s else "AI Research Score unavailable"
            lines.append(
                f"- {d.symbol}: P/E {_fmt_num(d.pe_ratio)}, ROE {_fmt_pct(d.roe)}, "
                f"revenue growth {_fmt_pct(d.revenue_growth)}, {score_part}."
            )

        best_score = max((c for c in contexts if c.score), key=lambda c: c.score.overall_score, default=None)
        cheapest = min(
            (c for c in contexts if c.detail.pe_ratio), key=lambda c: c.detail.pe_ratio, default=None
        )

        lines.append("")
        if best_score:
            lines.append(
                f"{best_score.detail.symbol} currently has the strongest overall research profile "
                f"among these based on financial, growth and technical metrics."
            )
        if cheapest:
            lines.append(
                f"{cheapest.detail.symbol} appears the least expensive on a P/E basis, though a "
                "lower multiple can also reflect slower growth or higher risk - it is not "
                "automatically the \"better\" choice."
            )
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    def answer_question(self, question: str, contexts: list[StockContext]) -> str:
        if not contexts:
            return (
                "I can research a specific company if you mention its name or symbol - for "
                "example \"Analyse Reliance Industries\" or \"Explain Tata Motors financial "
                "performance\". I can also compare two or three companies at once. "
                f"{DISCLAIMER}"
            )

        ctx = contexts[0]
        analysis = self.analyse_stock(ctx)
        return (
            f"{analysis.summary}\n\n"
            f"Financial health: {analysis.financial_health}\n\n"
            f"Growth: {analysis.growth}\n\n"
            f"Profitability: {analysis.profitability}\n\n"
            f"Valuation: {analysis.valuation}\n\n"
            f"Technical picture: {analysis.technical_picture}\n\n"
            f"{analysis.conclusion}\n\n{analysis.disclaimer}"
        )

    def answer_market_question(self, question: str, overview: MarketOverviewContext) -> str:
        as_of = overview.as_of.isoformat() if overview.as_of else "unavailable"
        lines = [f"Market data is as of {as_of} (under the '{overview.strategy_name}' strategy).", ""]

        if overview.top_gainers:
            lines.append("Top gainers:")
            lines += [
                f"- {g['symbol']} ({g['name']}): {_fmt_pct(g['change_percent'])}, Rs. {_fmt_num(g['latest_price'])}"
                for g in overview.top_gainers
            ]
            lines.append("")
        if overview.top_losers:
            lines.append("Top losers:")
            lines += [
                f"- {l['symbol']} ({l['name']}): {_fmt_pct(l['change_percent'])}, Rs. {_fmt_num(l['latest_price'])}"
                for l in overview.top_losers
            ]
            lines.append("")

        lines.append(
            f"{overview.advancers} of {overview.total_companies} tracked stocks advanced and "
            f"{overview.decliners} declined as of {as_of}."
        )
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    def answer_historical_price_question(self, question: str, context: HistoricalPriceContext) -> str:
        lines = []
        date_note = (
            f" ({context.requested_date.isoformat()} wasn't a trading day - showing the nearest "
            f"previous trading day instead)"
            if context.date_was_adjusted
            else ""
        )
        lines.append(
            f"On {context.resolved_date.isoformat()}{date_note}, {context.name} ({context.symbol}) "
            f"opened at Rs. {_fmt_num(context.open)}, reached a high of Rs. {_fmt_num(context.high)} "
            f"and a low of Rs. {_fmt_num(context.low)}, and closed at Rs. {_fmt_num(context.close)}, "
            f"on volume of {context.volume:,} shares."
        )
        lines.append("")
        lines.append(DISCLAIMER)
        return "\n".join(lines)

    # --- section builders -------------------------------------------------

    def _summary(self, ctx: StockContext) -> str:
        d, s = ctx.detail, ctx.score
        score_phrase = f"an AI Research Score of {s.overall_score}/100 ({s.label})" if s else "no computable AI Research Score yet"
        article = "an" if d.sector[:1].lower() in "aeiou" else "a"
        as_of = d.as_of.isoformat() if d.as_of else "an unspecified date"
        return (
            f"{d.name} ({d.symbol}) is {article} {d.sector} company currently trading at "
            f"Rs. {_fmt_num(d.latest_price)} as of {as_of} (under the '{ctx.strategy_name}' strategy), "
            f"with {score_phrase}."
        )

    def _financial_health(self, ctx: StockContext) -> str:
        d, s = ctx.detail, ctx.score
        de = d.debt_to_equity
        de_desc = "conservative" if de is not None and de < 0.5 else "moderate" if de is not None and de < 1.5 else "elevated" if de is not None else "unavailable"
        fs = s.subscores.financial_strength if s else None
        return (
            f"Debt/Equity is {_fmt_num(de)}, which looks {de_desc} for the sector. "
            f"The Financial Strength subscore is {_fmt_num(fs, 0)}/100."
        )

    def _growth(self, ctx: StockContext) -> str:
        d, s = ctx.detail, ctx.score
        rev_tier = _tier(d.revenue_growth, -5, 15)
        growth_score = s.subscores.growth if s else None
        return (
            f"Revenue grew {_fmt_pct(d.revenue_growth)} and net profit grew {_fmt_pct(d.profit_growth)} "
            f"in the latest reported year - a {rev_tier} growth trend overall "
            f"(Growth subscore {_fmt_num(growth_score, 0)}/100)."
        )

    def _profitability(self, ctx: StockContext) -> str:
        d, s = ctx.detail, ctx.score
        roe_tier = _tier(d.roe, 8, 20)
        profitability_score = s.subscores.profitability if s else None
        return (
            f"Return on equity is {_fmt_pct(d.roe)} and return on capital employed is {_fmt_pct(d.roce)}, "
            f"which is {roe_tier} profitability for the sector "
            f"(Profitability subscore {_fmt_num(profitability_score, 0)}/100)."
        )

    def _valuation(self, ctx: StockContext) -> str:
        d, s = ctx.detail, ctx.score
        valuation_score = s.subscores.valuation if s else None
        pe_desc = "expensive" if valuation_score is not None and valuation_score < 40 else "reasonable" if valuation_score is not None and valuation_score < 70 else "inexpensive" if valuation_score is not None else "unclear"
        return (
            f"At a P/E of {_fmt_num(d.pe_ratio)} and P/B of {_fmt_num(d.pb_ratio)}, the stock looks "
            f"relatively {pe_desc} versus sector peers (Valuation subscore {_fmt_num(valuation_score, 0)}/100)."
        )

    def _technical_picture(self, ctx: StockContext) -> str:
        t = ctx.technicals
        return (
            f"Trend is {t.trend.lower()} and momentum is {t.momentum.lower()}. RSI(14) is "
            f"{_fmt_num(t.rsi_14, 1)}, price is {_fmt_pct(t.price_vs_sma50_percent)} versus its 50-day "
            f"average and {_fmt_pct(t.price_vs_sma200_percent)} versus its 200-day average. Annualized "
            f"volatility is {_fmt_num(t.volatility, 1)}%."
        )

    def _strengths_and_risks(self, ctx: StockContext) -> tuple[list[str], list[str]]:
        s = ctx.score
        if s is None:
            return ["Data unavailable."], ["Data unavailable."]

        named = [
            ("Financial Strength", s.subscores.financial_strength),
            ("Growth", s.subscores.growth),
            ("Profitability", s.subscores.profitability),
            ("Valuation", s.subscores.valuation),
            ("Technical Momentum", s.subscores.technical_momentum),
        ]
        ranked = sorted(named, key=lambda item: item[1], reverse=True)

        strengths = [f"{name} scores {value:.0f}/100, the strongest area in this profile." for name, value in ranked[:2] if value >= 55]
        risks = [f"{name} scores only {value:.0f}/100, the weakest area in this profile." for name, value in ranked[-2:] if value < 55]

        if not strengths:
            strengths = ["No subscore currently stands out as a clear strength."]
        if not risks:
            risks = ["No subscore currently stands out as a clear weakness."]

        return strengths, risks

    def _things_to_monitor(self, ctx: StockContext) -> list[str]:
        d, t, s = ctx.detail, ctx.technicals, ctx.score
        items = []
        if d.debt_to_equity is not None and d.debt_to_equity > 1.2:
            items.append(f"Debt/Equity of {_fmt_num(d.debt_to_equity)} is on the higher side - watch interest costs and refinancing risk.")
        if t.volatility is not None and t.volatility > 30:
            items.append(f"Annualized volatility of {_fmt_num(t.volatility, 1)}% is elevated versus a typical large-cap.")
        if s and s.risk_label == "High":
            items.append("Overall risk profile is currently classified High - position sizing and diversification matter more here.")
        if not items:
            items.append("No specific red flags stand out in the current data; monitor quarterly results for changes in growth and margins.")
        return items

    def _conclusion(self, ctx: StockContext) -> str:
        s = ctx.score
        if s is None:
            return "An overall research conclusion is unavailable without a computed AI Research Score."
        return (
            f"Taken together, this profile is best described as \"{s.label}\" "
            f"({s.overall_score}/100) with {s.risk_label.lower()} classified risk. "
            "This reflects the data shown above, not a recommendation to buy or sell."
        )


class _PromptRewritingAIProvider(AIProvider):
    """Shared logic for providers that call a real LLM to rewrite the
    deterministic Mock draft into nicer prose. The LLM only ever rewrites
    text that already contains the real numbers - it never computes or
    invents them, and the grounded draft is always the fallback if the API
    call fails for any reason (missing key, network error, quota, etc.).
    Subclasses only need to implement `_generate()` and `provider_name`.
    """

    provider_name = "base"

    def _generate(self, prompt: str) -> str:
        raise NotImplementedError

    def _base_instructions(self) -> str:
        return (
            "You are a research assistant for an Indian stock research platform. "
            "Only use the numbers given below - never invent prices, ratios, or figures. "
            "If a figure says 'unavailable', say the data is unavailable rather than guessing. "
            "Never say 'Buy', 'Sell', 'Strong Buy', or give a target price - use neutral research "
            "language only (e.g. 'strong financial health', 'high valuation risk'). "
            "This is not personalized financial advice.\n\n"
        )

    def analyse_stock(self, context: StockContext) -> AIAnalysis:
        mock = MockAIProvider()
        skeleton = mock.analyse_stock(context)  # deterministic fallback + numeric grounding

        fields = {
            "SUMMARY": skeleton.summary,
            "FINANCIAL_HEALTH": skeleton.financial_health,
            "GROWTH": skeleton.growth,
            "PROFITABILITY": skeleton.profitability,
            "VALUATION": skeleton.valuation,
            "TECHNICAL_PICTURE": skeleton.technical_picture,
            "CONCLUSION": skeleton.conclusion,
        }
        prompt = (
            self._base_instructions()
            + "Rewrite EACH section below in clearer, more natural prose - one or two sentences "
            "per section, keeping every number exactly as given. This is not a chat message: "
            "each section is displayed separately under its own heading in the UI, so do not "
            "use markdown, headers, or bullet points, and do not repeat one section's content "
            "in another - plain sentences only, one topic per section. Respond with exactly "
            "one line per section, in this exact format and order, nothing else before or "
            "after:\n"
            + "".join(f"[{label}] <rewritten text>\n" for label in fields)
            + "\nSections to rewrite:\n"
            + "".join(f"[{label}] {text}\n" for label, text in fields.items())
        )
        try:
            text = self._generate(prompt)
            sections = _parse_labeled_sections(text)
        except Exception:
            return skeleton

        skeleton.summary = sections.get("SUMMARY") or skeleton.summary
        skeleton.financial_health = sections.get("FINANCIAL_HEALTH") or skeleton.financial_health
        skeleton.growth = sections.get("GROWTH") or skeleton.growth
        skeleton.profitability = sections.get("PROFITABILITY") or skeleton.profitability
        skeleton.valuation = sections.get("VALUATION") or skeleton.valuation
        skeleton.technical_picture = sections.get("TECHNICAL_PICTURE") or skeleton.technical_picture
        skeleton.conclusion = sections.get("CONCLUSION") or skeleton.conclusion
        skeleton.provider = self.provider_name
        return skeleton

    def compare_stocks(self, contexts: list[StockContext]) -> str:
        mock = MockAIProvider()
        draft = mock.compare_stocks(contexts)
        prompt = (
            self._base_instructions()
            + "Rewrite this comparison in clearer, more natural prose, keeping every number "
            "exactly as given and not adding any claim the draft doesn't already make. This is "
            "a chat message, so markdown (short bold labels, bullet points) is fine where it "
            "genuinely helps readability, but keep it concise - don't restate the same point "
            "twice.\n\n" + draft
        )
        try:
            return self._generate(prompt) or draft
        except Exception:
            return draft

    def answer_question(self, question: str, contexts: list[StockContext]) -> str:
        mock = MockAIProvider()
        draft = mock.answer_question(question, contexts)
        prompt = (
            self._base_instructions()
            + f'The user asked: "{question}"\n\n'
            + "Below is grounded reference data using only real computed numbers - never use a "
            "number that isn't in it, and never add a claim, opinion, or outside context it "
            "doesn't support. Answer the user's actual question directly and conversationally: "
            "don't recite every section if it isn't relevant to what was asked - a focused "
            "answer beats a full report dump. Markdown (short bold labels, bullet points) is "
            "fine where it genuinely helps readability, used sparingly.\n\n"
            + "Reference data:\n" + draft
        )
        try:
            return self._generate(prompt) or draft
        except Exception:
            return draft

    def answer_market_question(self, question: str, overview: MarketOverviewContext) -> str:
        mock = MockAIProvider()
        draft = mock.answer_market_question(question, overview)
        prompt = (
            self._base_instructions()
            + f'The user asked: "{question}"\n\n'
            + "Below is grounded market-wide reference data (today's top movers, advance/decline "
            "count, and the date it's as of) using only real computed numbers - never use a "
            "number that isn't in it. Answer the user's actual question directly and "
            "conversationally, always stating the date the data is as of somewhere in your "
            "answer. Markdown (short bold labels, bullet points) is fine where it genuinely "
            "helps readability.\n\n"
            + "Reference data:\n" + draft
        )
        try:
            return self._generate(prompt) or draft
        except Exception:
            return draft

    def answer_historical_price_question(self, question: str, context: HistoricalPriceContext) -> str:
        mock = MockAIProvider()
        draft = mock.answer_historical_price_question(question, context)
        prompt = (
            self._base_instructions()
            + f'The user asked: "{question}"\n\n'
            + "Below is the real OHLCV data for the specific date requested - never use a number "
            "that isn't in it, and never state a different date's figures as if they were the "
            "requested date's. If the date had to be adjusted (not a trading day), say so plainly. "
            "Answer directly and conversationally.\n\n"
            + "Reference data:\n" + draft
        )
        try:
            return self._generate(prompt) or draft
        except Exception:
            return draft


class GeminiAIProvider(_PromptRewritingAIProvider):
    """Google Gemini-backed provider. Requires GEMINI_API_KEY and GEMINI_MODEL.

    NOTE: this integration has not been exercised against a live API key in
    this environment - verify the model name and response shape against the
    current Gemini API docs before relying on it in production.
    """

    provider_name = "gemini"

    def __init__(self, api_key: str, model_name: str):
        self._api_key = api_key
        self._model_name = model_name

    def _generate(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model_name)
        response = model.generate_content(prompt)
        return (response.text or "").strip()


class GroqAIProvider(_PromptRewritingAIProvider):
    """Groq-backed provider (OpenAI-compatible chat completions API).
    Requires GROQ_API_KEY and GROQ_MODEL (e.g. "openai/gpt-oss-120b" - Groq's
    catalog changes over time, check https://console.groq.com/docs/models or
    GET https://api.groq.com/openai/v1/models with your key for current names).

    Verified working live against the Groq API (2026-09-25).
    """

    provider_name = "groq"
    _API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model_name: str):
        self._api_key = api_key
        self._model_name = model_name

    def _generate(self, prompt: str) -> str:
        import httpx

        response = httpx.post(
            self._API_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
