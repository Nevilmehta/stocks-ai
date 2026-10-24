from app.services import nifty_indices

NIFTY_BANK_CSV = (
    "Company Name,Industry,Symbol,Series,ISIN Code\n"
    "HDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034\n"
    "ICICI Bank Ltd.,Financial Services,ICICIBANK,EQ,INE090A01021\n"
)

NIFTY_IT_CSV = (
    "Company Name,Industry,Symbol,Series,ISIN Code\n"
    "Tata Consultancy Services Ltd.,Information Technology,TCS,EQ,INE467B01029\n"
    "Infosys Ltd.,Information Technology,INFY,EQ,INE009A01021\n"
)


def _fake_fetch(responses):
    def fetch(file_code):
        return list(__import__("csv").DictReader(__import__("io").StringIO(responses.get(file_code, ""))))

    return fetch


def test_build_sector_and_index_maps_merges_multiple_lists(monkeypatch):
    responses = {"ind_niftybanklist": NIFTY_BANK_CSV, "ind_niftyitlist": NIFTY_IT_CSV}
    monkeypatch.setattr(nifty_indices, "INDEX_SOURCES", {"NIFTY BANK": "ind_niftybanklist", "NIFTY IT": "ind_niftyitlist"})
    monkeypatch.setattr(nifty_indices, "fetch_index_constituents", _fake_fetch(responses))

    sectors, indices = nifty_indices.build_sector_and_index_maps()

    assert sectors["HDFCBANK"] == "Financial Services"
    assert sectors["TCS"] == "Information Technology"
    assert indices["HDFCBANK"] == ["NIFTY BANK"]
    assert indices["TCS"] == ["NIFTY IT"]


def test_build_sector_and_index_maps_collects_multiple_indices_per_symbol(monkeypatch):
    responses = {
        "ind_niftybanklist": NIFTY_BANK_CSV,
        "ind_nifty50list": "Company Name,Industry,Symbol,Series,ISIN Code\nHDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034\n",
    }
    monkeypatch.setattr(
        nifty_indices, "INDEX_SOURCES", {"NIFTY BANK": "ind_niftybanklist", "NIFTY 50": "ind_nifty50list"}
    )
    monkeypatch.setattr(nifty_indices, "fetch_index_constituents", _fake_fetch(responses))

    _, indices = nifty_indices.build_sector_and_index_maps()

    assert indices["HDFCBANK"] == ["NIFTY 50", "NIFTY BANK"]


def test_build_sector_and_index_maps_handles_unreachable_index(monkeypatch):
    monkeypatch.setattr(nifty_indices, "INDEX_SOURCES", {"NIFTY BANK": "ind_niftybanklist"})
    monkeypatch.setattr(nifty_indices, "fetch_index_constituents", lambda file_code: [])

    sectors, indices = nifty_indices.build_sector_and_index_maps()

    assert sectors == {}
    assert indices == {}


def test_index_sources_includes_broad_market_cap_coverage():
    # Regression guard: these two were added specifically to shrink the
    # "Unclassified" sector bucket (Nifty 500 alone only covers the top ~500
    # by market cap) - verified live against real niftyindices.com CSVs
    # before adding.
    assert nifty_indices.INDEX_SOURCES["NIFTY TOTAL MARKET"] == "ind_niftytotalmarket_list"
    assert nifty_indices.INDEX_SOURCES["NIFTY MICROCAP 250"] == "ind_niftymicrocap250_list"


def test_fetch_index_constituents_returns_empty_on_http_error(monkeypatch):
    import httpx

    def raise_error(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(nifty_indices.httpx, "get", raise_error)

    assert nifty_indices.fetch_index_constituents("ind_niftybanklist") == []
