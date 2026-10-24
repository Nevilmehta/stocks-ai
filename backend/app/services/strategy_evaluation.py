"""Preview and (basic) backtest support for admin-configured research
strategies. Kept separate from stocks.py's live-request path since these
endpoints evaluate every tracked company at once (preview) or replay
history (backtest), rather than answering a single per-stock request.

Backtest limitation, always returned to the caller rather than hidden: this
app's fundamentals (revenue/profit/ratios) aren't stored with a specific
per-period calendar date, only a fiscal-year/sequence - so the backtest can
vary technicals correctly over time (real daily price history exists) but
necessarily holds financials at "latest known" for every checkpoint. That's
a reasonable, clearly-labeled simplification for a "basic" backtest, not a
fabricated one.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.analytics.indicators_service import compute_technical_indicators
from app.analytics.scoring import compute_ai_score
from app.deps import ActiveStrategy
from app.models.company import Company
from app.models.financials import PeriodType
from app.models.price_history import PriceHistory
from app.providers.market_data import MarketDataProvider
from app.routers.stocks import get_stock_ai_score
from app.services.financial_periods import build_financial_periods
from app.schemas.strategy import BacktestCheckpoint, StrategyConfig, StrategyPreviewRow

BACKTEST_CAVEAT = (
    "Basic backtest only: technical indicators are recomputed point-in-time from real daily "
    "price history, but financials/ratios (revenue, profit, P/E, etc.) are not stored with a "
    "specific calendar date in this app, so every checkpoint uses each company's latest "
    "available financials rather than what was actually known on that date. No portfolio "
    "simulation or position sizing is performed - this shows score-vs-forward-return only."
)

_NUM_CHECKPOINTS = 6
_LOOKBACK_ROWS = 500  # roughly the last ~2 years of trading days
_FORWARD_30 = 30
_FORWARD_90 = 90
_MIN_ROWS_REQUIRED = 260

# Preview computes a full AI score twice per company (active + proposed
# config) - at the full ~2,660-company NSE universe that's thousands of
# technicals+score computations in one synchronous request. Capped the same
# way screener.py caps its single-pass scoring, just lower since this does
# 2x the work per company.
MAX_PREVIEW_COMPANIES = 150
# Backtest multiplies company count by _NUM_CHECKPOINTS x 2 configs - only
# matters when no explicit `symbols` filter narrows it (the admin UI always
# passes one; this guards the "preview against everything" edge case).
MAX_BACKTEST_COMPANIES = 50


def run_preview(
    provider: MarketDataProvider, active: ActiveStrategy, proposed_config: StrategyConfig
) -> list[StrategyPreviewRow]:
    """Recomputes each tracked company's AI score under the proposed config,
    alongside the currently-active one, using today's data. Read-only."""
    proposed = ActiveStrategy(name="(preview)", config=proposed_config)
    companies = provider.search_stocks("", limit=5000)[:MAX_PREVIEW_COMPANIES]

    rows: list[StrategyPreviewRow] = []
    for company in companies:
        try:
            active_score = get_stock_ai_score(company.symbol, provider, active)
        except HTTPException:
            active_score = None
        try:
            proposed_score = get_stock_ai_score(company.symbol, provider, proposed)
        except HTTPException:
            proposed_score = None

        if active_score is None and proposed_score is None:
            continue

        delta = (
            proposed_score.overall_score - active_score.overall_score
            if active_score and proposed_score
            else None
        )
        rows.append(
            StrategyPreviewRow(
                symbol=company.symbol,
                name=company.name,
                active_score=active_score.overall_score if active_score else None,
                active_label=active_score.label if active_score else None,
                proposed_score=proposed_score.overall_score if proposed_score else None,
                proposed_label=proposed_score.label if proposed_score else None,
                delta=delta,
            )
        )

    rows.sort(key=lambda r: abs(r.delta) if r.delta is not None else -1, reverse=True)
    return rows


def run_backtest(
    db: Session,
    provider: MarketDataProvider,
    active: ActiveStrategy,
    proposed_config: StrategyConfig,
    symbols: list[str] | None,
) -> list[BacktestCheckpoint]:
    query = db.query(Company)
    if symbols:
        query = query.filter(Company.symbol.in_([s.upper() for s in symbols]))
        companies = query.all()
    else:
        companies = query.order_by(Company.name).limit(MAX_BACKTEST_COMPANIES).all()

    checkpoints: list[BacktestCheckpoint] = []
    for company in companies:
        all_rows = (
            db.query(PriceHistory)
            .filter(PriceHistory.company_id == company.id)
            .order_by(PriceHistory.date.asc())
            .all()
        )
        if len(all_rows) < _MIN_ROWS_REQUIRED:
            continue

        usable_rows = all_rows[-_LOOKBACK_ROWS:] if len(all_rows) > _LOOKBACK_ROWS else all_rows
        candidate_end = len(usable_rows) - _FORWARD_90
        if candidate_end <= 0:
            continue

        step = max(1, candidate_end // _NUM_CHECKPOINTS)
        checkpoint_indices = list(range(step, candidate_end + 1, step))[:_NUM_CHECKPOINTS]
        if not checkpoint_indices:
            continue

        annual_periods = [p for p in build_financial_periods(provider, company.symbol) if p.period_type == PeriodType.annual]
        if not annual_periods:
            continue

        peer_companies = provider.get_companies_by_sector(company.sector, exclude_symbol=company.symbol)
        peer_latest_periods = []
        for peer in peer_companies:
            peer_annual = [p for p in build_financial_periods(provider, peer.symbol) if p.period_type == PeriodType.annual]
            if peer_annual:
                peer_latest_periods.append(peer_annual[-1])

        for idx in checkpoint_indices:
            checkpoint_row = usable_rows[idx]
            price_rows_upto = usable_rows[: idx + 1]

            technicals_active = compute_technical_indicators(price_rows_upto, active.config)
            technicals_proposed = compute_technical_indicators(price_rows_upto, proposed_config)

            active_result = compute_ai_score(annual_periods, technicals_active, peer_latest_periods, active.config)
            proposed_result = compute_ai_score(annual_periods, technicals_proposed, peer_latest_periods, proposed_config)

            forward_30_row = usable_rows[idx + _FORWARD_30] if idx + _FORWARD_30 < len(usable_rows) else None
            forward_90_row = usable_rows[idx + _FORWARD_90] if idx + _FORWARD_90 < len(usable_rows) else None
            checkpoint_close = float(checkpoint_row.close)

            def _pct(row: PriceHistory | None) -> float | None:
                if row is None or not checkpoint_close:
                    return None
                return round((float(row.close) - checkpoint_close) / checkpoint_close * 100, 2)

            checkpoints.append(
                BacktestCheckpoint(
                    symbol=company.symbol,
                    checkpoint_date=checkpoint_row.date,
                    active_score=active_result.overall_score if active_result else None,
                    proposed_score=proposed_result.overall_score if proposed_result else None,
                    forward_return_30d=_pct(forward_30_row),
                    forward_return_90d=_pct(forward_90_row),
                )
            )

    return checkpoints
