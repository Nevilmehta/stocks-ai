"""Fetches NSE's official Nifty index constituent lists from niftyindices.com
(a free, public, no-auth CSV per index - verified during design to need only
a normal User-Agent header, unlike the bhavcopy archives which need the
Akamai cookie workaround). Each list already includes an "Industry" column
per company, so the same fetch doubles as both sector classification and
index-membership data.

Not every NSE-listed company appears in any of these lists (small/micro caps
mostly don't) - those companies simply get no index memberships and an
"Unclassified" sector, which is an accepted, known limitation, not a bug.
"""

from __future__ import annotations

import csv
import io

import httpx

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Order matters only in that earlier entries get first say on a company's
# sector if it appears in more than one list - in practice the Industry
# value is consistent across lists for the same company either way.
INDEX_SOURCES: dict[str, str] = {
    "NIFTY BANK": "ind_niftybanklist",
    "NIFTY IT": "ind_niftyitlist",
    "NIFTY AUTO": "ind_niftyautolist",
    "NIFTY PHARMA": "ind_niftypharmalist",
    "NIFTY FMCG": "ind_niftyfmcglist",
    "NIFTY METAL": "ind_niftymetallist",
    "NIFTY REALTY": "ind_niftyrealtylist",
    "NIFTY ENERGY": "ind_niftyenergylist",
    "NIFTY MEDIA": "ind_niftymedialist",
    "NIFTY FINANCIAL SERVICES": "ind_niftyfinservicelist",
    "NIFTY HEALTHCARE": "ind_niftyhealthcarelist",
    "NIFTY CONSUMER DURABLES": "ind_niftyconsumerdurableslist",
    "NIFTY OIL AND GAS": "ind_niftyoilgaslist",
    "NIFTY 50": "ind_nifty50list",
    "NIFTY NEXT 50": "ind_niftynext50list",
    "NIFTY 100": "ind_nifty100list",
    "NIFTY 200": "ind_nifty200list",
    "NIFTY 500": "ind_nifty500list",
    "NIFTY MIDCAP 50": "ind_niftymidcap50list",
    "NIFTY SMALLCAP 50": "ind_niftysmallcap50list",
    # Broader market-cap coverage, added to shrink the "Unclassified" bucket -
    # verified live before adding (same CSV format, real Industry column).
    # Nifty 500 (already above) only covers the top ~500 by free-float market
    # cap; these two extend coverage further down the universe.
    "NIFTY TOTAL MARKET": "ind_niftytotalmarket_list",
    "NIFTY MICROCAP 250": "ind_niftymicrocap250_list",
}


def fetch_index_constituents(file_code: str) -> list[dict[str, str]]:
    """Returns rows as dicts with keys: Company Name, Industry, Symbol,
    Series, ISIN Code. Returns [] (not an error) if the index isn't
    reachable - callers should treat a missing index as "skip it", not fail
    the whole run over one unavailable list."""
    url = f"https://niftyindices.com/IndexConstituent/{file_code}.csv"
    try:
        response = httpx.get(url, headers={"User-Agent": _USER_AGENT}, timeout=20.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return []
    return list(csv.DictReader(io.StringIO(response.text)))


def build_sector_and_index_maps() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Fetches every list in INDEX_SOURCES once and merges them into:
    - symbol -> sector (Industry column, first list that has it wins)
    - symbol -> sorted list of index names the symbol appears in
    """
    sector_by_symbol: dict[str, str] = {}
    indices_by_symbol: dict[str, set[str]] = {}

    for index_name, file_code in INDEX_SOURCES.items():
        for row in fetch_index_constituents(file_code):
            symbol = row.get("Symbol", "").strip()
            if not symbol:
                continue
            industry = row.get("Industry", "").strip()

            sector_by_symbol.setdefault(symbol, industry or "Unclassified")
            indices_by_symbol.setdefault(symbol, set()).add(index_name)

    return sector_by_symbol, {symbol: sorted(names) for symbol, names in indices_by_symbol.items()}
