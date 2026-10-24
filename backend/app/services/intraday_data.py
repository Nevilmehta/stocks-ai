"""Fetches free, unofficial intraday (1-minute) OHLCV bars for NSE stocks via
Yahoo Finance's undocumented chart API - the only free source found for this
(NSE's own bhavcopy is end-of-day only; NSE's live-quote API was already
confirmed this session to sit behind a harder Akamai tier than bhavcopy,
effectively unusable for free/unofficial access).

Empirically verified live before building this (not guessed):
- `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}.NS?interval=1m&range=5d`
  returns real 1-minute bars for NSE stocks, correctly scoped to NSE's actual
  09:15-15:30 IST session, for both large caps (TCS, RELIANCE) and small caps
  (20MICRONS) via a plain `{symbol}.NS` ticker.
- It is genuinely unofficial - no published docs, no uptime/format guarantee.
  Degrades to None on any failure; never raises.
- Rapid consecutive requests trigger a block that can last tens of seconds
  (plain 404, not 429) even for valid, well-known symbols - confirmed by
  hitting 5 symbols in immediate succession and seeing every one 404,
  including ones later confirmed fine in isolation (even an 8-second gap
  wasn't always enough to recover). This means callers must only ever fetch
  ONE symbol on-demand (a user opening a single stock's intraday view),
  never loop this across many companies the way the bhavcopy/backfill
  scripts do for daily data - there's no bulk-safe way to use this endpoint,
  and a 404 here doesn't reliably mean "this symbol has no data" (it may
  just mean "try again in a bit").
- Coverage is plausibly not 100% universal (Yahoo's ticker database won't
  necessarily have every NSE symbol under a plain {symbol}.NS mapping), but
  this was never actually confirmed for any specific real symbol - an
  earlier test run that looked like a genuine gap (TATAMOTORS/TMCV) turned
  out, on a cleaner retest, to just be the rate-limit above. Callers should
  still treat "no data" as a normal, expected outcome rather than an error,
  just without assuming any particular company is a known permanent gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
_IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class IntradayBar:
    time: datetime  # timezone-aware, IST
    open: float
    high: float
    low: float
    close: float
    volume: int


def fetch_latest_intraday_session(nse_symbol: str) -> tuple[date, list[IntradayBar]] | None:
    """Returns (trading_date, bars) for the most recent trading session with
    data (today's so-far session if the market is open, otherwise the last
    completed session), or None if unavailable for any reason - never
    raises, so callers can show a plain "not available" message rather than
    an error."""
    try:
        response = httpx.get(
            _CHART_URL.format(symbol=nse_symbol.upper()),
            params={"interval": "1m", "range": "5d"},
            headers={"User-Agent": _USER_AGENT},
            timeout=15.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    results = ((payload.get("chart") or {}).get("result")) or []
    if not results:
        return None

    chart = results[0]
    timestamps = chart.get("timestamp") or []
    quotes = (chart.get("indicators") or {}).get("quote") or []
    if not timestamps or not quotes:
        return None
    quote = quotes[0]

    bars_by_date: dict[date, list[IntradayBar]] = {}
    for i, ts in enumerate(timestamps):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        if o is None or h is None or l is None or c is None:
            continue  # gaps are a normal, expected part of this free feed
        volume = quote["volume"][i] if i < len(quote.get("volume", [])) else None
        dt = datetime.fromtimestamp(ts, tz=_IST)
        bars_by_date.setdefault(dt.date(), []).append(
            IntradayBar(time=dt, open=float(o), high=float(h), low=float(l), close=float(c), volume=int(volume or 0))
        )

    if not bars_by_date:
        return None
    latest_date = max(bars_by_date)
    return latest_date, sorted(bars_by_date[latest_date], key=lambda b: b.time)
