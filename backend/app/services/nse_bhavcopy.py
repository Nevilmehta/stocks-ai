"""Fetches and parses NSE's daily "bhavcopy" file - one free CSV per trading
day covering every listed stock's OHLCV. No API key required, but NSE's file
server sits behind Akamai bot protection: plain requests get a 503, so real
browser-like headers (and, for the legacy URL, a cookie bootstrap) are needed.

Two URL formats exist, split by date (both verified working during design):
- legacy: works up to ~2024-07-01, 404s afterwards.
- current (UDiFF): works from ~2024-07-01 onward.

This module is fetch + parse only - no DB access, no company-list knowledge -
so parsing can be unit tested with fixture CSV text and zero network calls.
See app/services/market_data_sync.py for the DB upsert layer that uses this.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime

import httpx

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_REFERER = "https://www.nseindia.com/all-reports"
_HOMEPAGE_URL = "https://www.nseindia.com/"

_LEGACY_FORMAT_CUTOFF = date(2024, 7, 1)


@dataclass
class BhavcopyRow:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def _legacy_url(trade_date: date) -> str:
    day = trade_date.strftime("%d").upper()
    month = trade_date.strftime("%b").upper()
    year = trade_date.strftime("%Y")
    return (
        f"https://archives.nseindia.com/content/historical/EQUITIES/"
        f"{year}/{month}/cm{day}{month}{year}bhav.csv.zip"
    )


def _current_url(trade_date: date) -> str:
    return (
        "https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{trade_date:%Y%m%d}_F_0000.csv.zip"
    )


def bhavcopy_url(trade_date: date) -> str:
    if trade_date < _LEGACY_FORMAT_CUTOFF:
        return _legacy_url(trade_date)
    return _current_url(trade_date)


_UDIFF_FILENAME_RE = re.compile(r"BhavCopy_NSE_CM_0_0_0_(\d{8})_F_0000\.csv", re.IGNORECASE)
_LEGACY_FILENAME_RE = re.compile(r"cm(\d{2}[A-Z]{3}\d{4})bhav\.csv", re.IGNORECASE)


def infer_trade_date_from_filename(filename: str) -> date | None:
    """Best-effort trade date extraction from an official NSE bhavcopy filename
    (either format), so an admin re-uploading the file exactly as downloaded
    from nseindia.com/all-reports doesn't also have to type the date in by
    hand. Returns None if the filename doesn't match either known pattern -
    callers should then require an explicit date instead of guessing."""
    match = _UDIFF_FILENAME_RE.search(filename)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%d").date()

    match = _LEGACY_FILENAME_RE.search(filename)
    if match:
        return datetime.strptime(match.group(1).upper(), "%d%b%Y").date()

    return None


def parse_legacy_csv(csv_text: str) -> list[BhavcopyRow]:
    rows: list[BhavcopyRow] = []
    for record in csv.DictReader(io.StringIO(csv_text)):
        if record.get("SERIES", "").strip() != "EQ":
            continue
        rows.append(
            BhavcopyRow(
                symbol=record["SYMBOL"].strip(),
                open=float(record["OPEN"]),
                high=float(record["HIGH"]),
                low=float(record["LOW"]),
                close=float(record["CLOSE"]),
                volume=int(float(record["TOTTRDQTY"])),
            )
        )
    return rows


def parse_current_csv(csv_text: str) -> list[BhavcopyRow]:
    rows: list[BhavcopyRow] = []
    for record in csv.DictReader(io.StringIO(csv_text)):
        if record.get("SctySrs", "").strip() != "EQ":
            continue
        rows.append(
            BhavcopyRow(
                symbol=record["TckrSymb"].strip(),
                open=float(record["OpnPric"]),
                high=float(record["HghPric"]),
                low=float(record["LwPric"]),
                close=float(record["ClsPric"]),
                volume=int(float(record["TtlTradgVol"])),
            )
        )
    return rows


def parse_bhavcopy_zip(trade_date: date, zip_bytes: bytes) -> list[BhavcopyRow]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        csv_name = archive.namelist()[0]
        csv_text = archive.read(csv_name).decode("utf-8")

    if trade_date < _LEGACY_FORMAT_CUTOFF:
        return parse_legacy_csv(csv_text)
    return parse_current_csv(csv_text)


def _get(client: httpx.Client, url: str) -> httpx.Response:
    return client.get(url, headers={"User-Agent": _USER_AGENT, "Referer": _REFERER})


def fetch_bhavcopy(trade_date: date) -> list[BhavcopyRow] | None:
    """Returns None for a non-trading date (weekend/holiday - a 404 from NSE),
    never for a real failure. Raises on anything else (network error, or still
    blocked after a cookie-bootstrap retry) so callers can tell "no data today"
    apart from "something's actually wrong"."""
    url = bhavcopy_url(trade_date)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = _get(client, url)

        if response.status_code in (403, 503):
            # Akamai bot-mitigation cookies get set even on a blocked response -
            # bootstrapping against the homepage first (ignoring its own status)
            # is enough to unblock the archive request, verified during design.
            client.get(_HOMEPAGE_URL, headers={"User-Agent": _USER_AGENT})
            response = _get(client, url)

        if response.status_code == 404:
            return None
        response.raise_for_status()

        return parse_bhavcopy_zip(trade_date, response.content)
