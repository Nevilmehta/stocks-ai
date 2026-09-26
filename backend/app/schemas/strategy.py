"""StrategyConfig is the single source of truth for what's admin-configurable
in the indicator/scoring engine. Every default below matches today's
hardcoded values exactly (app/analytics/technicals.py, indicators_service.py,
scoring.py) - so until an admin creates and activates a different strategy,
every computation is bit-for-bit identical to before this feature existed.

Indicator enable/disable flags are cosmetic only (v1 scope, by explicit user
choice): they tell the frontend what to render, but a disabled indicator
still quietly feeds the AI score exactly as before. Full exclude-and-reweight
is a possible future extension, not built now.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator


class StrategyConfig(BaseModel):
    # --- indicator toggles (cosmetic only - see module docstring) ---
    enable_sma: bool = True
    enable_ema: bool = True
    enable_rsi: bool = True
    enable_macd: bool = True
    enable_bollinger: bool = True

    # --- indicator periods/parameters ---
    sma_short: int = 20
    sma_medium: int = 50
    sma_long: int = 200
    ema_short: int = 20
    ema_medium: int = 50
    ema_long: int = 200
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger_period: int = 20
    bollinger_num_std: float = 2.0

    # --- AI research score weights (must sum to ~1.0) ---
    weight_financial_strength: float = 0.25
    weight_growth: float = 0.20
    weight_profitability: float = 0.20
    weight_valuation: float = 0.15
    weight_technical_momentum: float = 0.10
    weight_risk: float = 0.10

    # --- curated subset of scoring thresholds (not every internal magic
    # number - scoped to what's realistic for a researcher to tune in v1) ---
    debt_to_equity_good: float = 0.0
    debt_to_equity_bad: float = 2.5
    roe_low: float = 5.0
    roe_high: float = 30.0
    roce_low: float = 5.0
    roce_high: float = 30.0
    pe_fallback_low: float = 10.0
    pe_fallback_high: float = 45.0
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    risk_low_cutoff: float = 70.0
    risk_moderate_cutoff: float = 40.0
    overall_very_strong_cutoff: float = 85.0
    overall_strong_cutoff: float = 70.0
    overall_balanced_cutoff: float = 50.0
    overall_weak_cutoff: float = 30.0

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "StrategyConfig":
        total = (
            self.weight_financial_strength
            + self.weight_growth
            + self.weight_profitability
            + self.weight_valuation
            + self.weight_technical_momentum
            + self.weight_risk
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Score weights must sum to 1.0 (got {total:.3f})")
        return self


DEFAULT_STRATEGY_CONFIG = StrategyConfig()


class StrategyCreateRequest(BaseModel):
    name: str
    description: str = ""
    config: StrategyConfig


class StrategyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: StrategyConfig | None = None


class StrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    config: StrategyConfig
    is_active: bool
    created_at: datetime


class StrategyPreviewRequest(BaseModel):
    config: StrategyConfig


class StrategyPreviewRow(BaseModel):
    symbol: str
    name: str
    active_score: int | None
    active_label: str | None
    proposed_score: int | None
    proposed_label: str | None
    delta: int | None


class StrategyPreviewResponse(BaseModel):
    active_strategy_name: str
    results: list[StrategyPreviewRow]


class StrategyBacktestRequest(BaseModel):
    config: StrategyConfig
    symbols: list[str] | None = None


class BacktestCheckpoint(BaseModel):
    symbol: str
    checkpoint_date: date
    active_score: int | None
    proposed_score: int | None
    forward_return_30d: float | None
    forward_return_90d: float | None


class StrategyBacktestResponse(BaseModel):
    active_strategy_name: str
    checkpoints: list[BacktestCheckpoint]
    caveat: str
