from pydantic import BaseModel


class SmartIndicatorRow(BaseModel):
    symbol: str
    name: str
    sector: str

    latest_price: float | None
    change_percent: float | None
    volume: int | None
    return_1d: float | None
    return_1w: float | None
    return_1m: float | None
    pe_ratio: float | None

    rsi_14: float | None
    trend: str
    swing_structure: str
    nearest_fibonacci_level: str | None

    signal: str
    signal_reasons: list[str]

    indicator: str
    indicator_label: str
    indicator_value: float | None


class IndicatorOption(BaseModel):
    key: str
    label: str


class SmartIndicatorMeta(BaseModel):
    available_indicators: list[IndicatorOption]
    default_indicator: str
