from app.routers import admin as admin_router
from tests.test_admin_analytics import _login_admin
from tests.test_research import _seed_company


def test_sync_rejected_when_not_real_provider(client, db_session):
    _login_admin(client, db_session)

    response = client.post("/api/admin/market-data/sync", json={})

    assert response.status_code == 400


def test_sync_upserts_price_history_when_real_provider(client, db_session, monkeypatch):
    monkeypatch.setattr(admin_router.get_settings(), "market_data_provider", "real")
    monkeypatch.setattr(admin_router, "sync_price_history_for_date", lambda db, trade_date: 1)
    monkeypatch.setattr(admin_router, "refresh_financial_ratios_from_latest_price", lambda db, company: None)

    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = client.post("/api/admin/market-data/sync", json={"trade_date": "2024-01-02"})

    assert response.status_code == 200
    body = response.json()
    assert body["trade_date"] == "2024-01-02"
    assert body["rows_synced"] == 1
