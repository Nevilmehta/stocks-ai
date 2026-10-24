"""Detects "what was X's price on <date>" style chat questions and looks up
the real historical OHLCV row for that exact date - not just the latest
snapshot build_stock_context normally provides. Kept separate from
stock_context.py since this is a different shape of question (a specific
past date, not "current state").
"""

from __future__ import annotations

from datetime import date, timedelta

from dateutil import parser as date_parser

from app.providers.ai_provider import HistoricalPriceContext
from app.providers.market_data import MarketDataProvider

# Only attempt date extraction when the message also looks like it's asking
# about a price/value - keeps this from misfiring on ordinary questions that
# happen to contain a number (e.g. "TCS's 2024 revenue growth").
_PRICE_KEYWORDS = (
    "price", "close", "closing", "closed", "open", "opening", "opened",
    "high", "low", "volume", "traded", "trading", "worth", "value",
)

_MAX_LOOKBACK_DAYS = 7  # how far back to search for the nearest trading day


def is_price_lookup_question(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _PRICE_KEYWORDS)


def extract_date_from_message(message: str, today: date) -> date | None:
    """Returns None (not an error) if the message doesn't contain a
    recognizable date - callers should treat that as "no specific date was
    asked about", not "something went wrong"."""
    lowered = message.lower()
    if "yesterday" in lowered:
        return today - timedelta(days=1)
    if "today" in lowered:
        return today

    try:
        parsed = date_parser.parse(message, fuzzy=True, default=_default_datetime(today))
    except (ValueError, OverflowError):
        return None
    return parsed.date()


def _default_datetime(today: date):
    from datetime import datetime

    return datetime(today.year, today.month, today.day)


def lookup_historical_price(
    provider: MarketDataProvider, symbol: str, name: str, requested_date: date
) -> HistoricalPriceContext | None:
    """Looks for an exact PriceHistory row on requested_date; if that wasn't a
    trading day (weekend/holiday), walks back up to _MAX_LOOKBACK_DAYS to find
    the nearest previous one. Returns None if nothing is found in range at
    all (date too far in the past/future for the data this app has)."""
    rows = provider.get_price_history(symbol, timeframe="MAX")
    if not rows:
        return None

    by_date = {row.date: row for row in rows}

    for offset in range(_MAX_LOOKBACK_DAYS + 1):
        candidate = requested_date - timedelta(days=offset)
        row = by_date.get(candidate)
        if row is not None:
            return HistoricalPriceContext(
                symbol=symbol,
                name=name,
                requested_date=requested_date,
                resolved_date=candidate,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=row.volume,
            )

    return None


def available_date_range(provider: MarketDataProvider, symbol: str) -> tuple[date, date] | None:
    """Used to build an honest "no data for that date" message with the
    actual range this app does have, instead of a bare refusal."""
    rows = provider.get_price_history(symbol, timeframe="MAX")
    if not rows:
        return None
    return rows[0].date, rows[-1].date
