from datetime import date, datetime, timedelta, timezone

from app.routers import stocks
from app.services.intraday_data import IntradayBar
from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def test_intraday_requires_authentication(client):
    response = client.get("/api/stocks/TCS/intraday")
    assert response.status_code == 401


def test_intraday_404s_for_unknown_company(client, db_session):
    _login(client, db_session)
    response = client.get("/api/stocks/NOTREAL/intraday")
    assert response.status_code == 404


def test_intraday_returns_bars_when_available(client, db_session, monkeypatch):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    IST = timezone(timedelta(hours=5, minutes=30))
    trading_date = date(2025, 10, 23)
    bars = [
        IntradayBar(time=datetime(2025, 10, 23, 9, 15, tzinfo=IST), open=2500, high=2505, low=2498, close=2502, volume=10000),
        IntradayBar(time=datetime(2025, 10, 23, 9, 16, tzinfo=IST), open=2502, high=2504, low=2500, close=2503, volume=8000),
    ]
    monkeypatch.setattr(stocks, "fetch_latest_intraday_session", lambda symbol: (trading_date, bars))

    response = client.get("/api/stocks/TCS/intraday")
    assert response.status_code == 200
    body = response.json()
    assert body["trading_date"] == "2025-10-23"
    assert len(body["points"]) == 2
    assert body["points"][0]["close"] == 2502


def test_intraday_returns_empty_points_not_an_error_when_unavailable(client, db_session, monkeypatch):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    monkeypatch.setattr(stocks, "fetch_latest_intraday_session", lambda symbol: None)

    response = client.get("/api/stocks/TCS/intraday")
    assert response.status_code == 200
    body = response.json()
    assert body["trading_date"] is None
    assert body["points"] == []
