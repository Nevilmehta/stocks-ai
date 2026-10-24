import httpx

from app.services import intraday_data
from app.services.intraday_data import fetch_latest_intraday_session

_SAMPLE_RESPONSE = {
    "chart": {
        "result": [
            {
                "meta": {"symbol": "TCS.NS", "currency": "INR"},
                "timestamp": [
                    1761111300,  # 2025-10-22 09:15 IST
                    1761111360,  # 2025-10-22 09:16 IST
                    1761197700,  # 2025-10-23 09:15 IST
                    1761197760,  # 2025-10-23 09:16 IST
                ],
                "indicators": {
                    "quote": [
                        {
                            "open": [2500.0, 2501.0, 2510.0, None],
                            "high": [2505.0, 2503.0, 2515.0, None],
                            "low": [2498.0, 2499.0, 2508.0, None],
                            "close": [2502.0, 2500.5, 2512.0, None],
                            "volume": [10000, 8000, 12000, None],
                        }
                    ]
                },
            }
        ],
        "error": None,
    }
}


def test_fetch_latest_intraday_session_returns_most_recent_trading_day(monkeypatch):
    def _fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json=_SAMPLE_RESPONSE, request=httpx.Request("GET", url))

    monkeypatch.setattr(intraday_data.httpx, "get", _fake_get)

    result = fetch_latest_intraday_session("TCS")
    assert result is not None
    trading_date, bars = result

    assert trading_date.isoformat() == "2025-10-23"
    # The 4th bar (None OHLC) is a gap and must be skipped, not crash.
    assert len(bars) == 1
    assert bars[0].close == 2512.0
    assert bars[0].volume == 12000


def test_fetch_latest_intraday_session_returns_none_on_http_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(intraday_data.httpx, "get", _raise)

    assert fetch_latest_intraday_session("TCS") is None


def test_fetch_latest_intraday_session_returns_none_on_404(monkeypatch):
    def _fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(intraday_data.httpx, "get", _fake_get)

    assert fetch_latest_intraday_session("NOTREAL") is None


def test_fetch_latest_intraday_session_returns_none_when_no_result(monkeypatch):
    def _fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json={"chart": {"result": None, "error": {"code": "Not Found"}}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(intraday_data.httpx, "get", _fake_get)

    assert fetch_latest_intraday_session("TATAMOTORS") is None


def test_fetch_latest_intraday_session_returns_none_when_every_bar_is_a_gap(monkeypatch):
    empty_response = {
        "chart": {
            "result": [
                {
                    "timestamp": [1761197700],
                    "indicators": {"quote": [{"open": [None], "high": [None], "low": [None], "close": [None], "volume": [None]}]},
                }
            ]
        }
    }

    def _fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json=empty_response, request=httpx.Request("GET", url))

    monkeypatch.setattr(intraday_data.httpx, "get", _fake_get)

    assert fetch_latest_intraday_session("TCS") is None
