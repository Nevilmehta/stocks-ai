from datetime import date, timedelta

from app.models.price_history import PriceHistory
from app.models.strategy import ResearchStrategy
from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG
from tests.test_admin_analytics import _login_admin
from tests.test_research import _create_user, _seed_company


def _valid_config_payload(**overrides) -> dict:
    payload = DEFAULT_STRATEGY_CONFIG.model_dump()
    payload.update(overrides)
    return payload


def _seed_company_with_long_history(db_session, symbol: str, name: str, days: int = 400):
    """_seed_company gives 10 days + financials/ratios - extend with enough
    additional history for the backtest's point-in-time checkpoints + forward
    return window to have something to work with."""
    company = _seed_company(db_session, symbol, name)
    start = date.today() - timedelta(days=days + 30)
    price = 100.0
    for i in range(days):
        price *= 1.001
        db_session.add(
            PriceHistory(
                company_id=company.id,
                date=start + timedelta(days=i),
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=100000,
            )
        )
    db_session.commit()
    return company


def test_strategy_endpoints_require_admin(client, db_session):
    _create_user(db_session, email="user@example.com")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    assert client.get("/api/admin/strategies").status_code == 403
    assert client.post("/api/admin/strategies", json={"name": "x", "config": _valid_config_payload()}).status_code == 403


def test_default_config_matches_hardcoded_defaults(client, db_session):
    _login_admin(client, db_session)
    response = client.get("/api/admin/strategies/default-config")
    assert response.status_code == 200
    assert response.json()["rsi_period"] == 14
    assert response.json()["weight_growth"] == 0.20


def test_create_and_list_strategy(client, db_session):
    _login_admin(client, db_session)

    response = client.post(
        "/api/admin/strategies",
        json={"name": "Aggressive Growth", "description": "Weighs growth more heavily", "config": _valid_config_payload()},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Aggressive Growth"
    assert created["is_active"] is False

    listed = client.get("/api/admin/strategies").json()
    assert any(s["id"] == created["id"] for s in listed)


def test_invalid_weights_rejected(client, db_session):
    _login_admin(client, db_session)
    bad_config = _valid_config_payload(weight_financial_strength=0.9)
    response = client.post("/api/admin/strategies", json={"name": "Bad", "config": bad_config})
    assert response.status_code == 422


def test_update_strategy(client, db_session):
    _login_admin(client, db_session)
    created = client.post(
        "/api/admin/strategies", json={"name": "Original", "config": _valid_config_payload()}
    ).json()

    response = client.patch(f"/api/admin/strategies/{created['id']}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_activate_deactivates_others(client, db_session):
    _login_admin(client, db_session)
    first = client.post("/api/admin/strategies", json={"name": "First", "config": _valid_config_payload()}).json()
    second = client.post("/api/admin/strategies", json={"name": "Second", "config": _valid_config_payload()}).json()

    client.post(f"/api/admin/strategies/{first['id']}/activate")
    client.post(f"/api/admin/strategies/{second['id']}/activate")

    rows = db_session.query(ResearchStrategy).all()
    active_rows = [r for r in rows if r.is_active]
    assert len(active_rows) == 1
    assert str(active_rows[0].id) == second["id"]


def test_restore_previous_strategy_by_reactivating(client, db_session):
    _login_admin(client, db_session)
    first = client.post("/api/admin/strategies", json={"name": "First", "config": _valid_config_payload()}).json()
    second = client.post("/api/admin/strategies", json={"name": "Second", "config": _valid_config_payload()}).json()

    client.post(f"/api/admin/strategies/{first['id']}/activate")
    client.post(f"/api/admin/strategies/{second['id']}/activate")
    response = client.post(f"/api/admin/strategies/{first['id']}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_preview_returns_score_comparison(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    proposed = _valid_config_payload(rsi_period=21)
    response = client.post("/api/admin/strategies/preview", json={"config": proposed})

    assert response.status_code == 200
    body = response.json()
    assert body["active_strategy_name"] == "Default"
    symbols = [r["symbol"] for r in body["results"]]
    assert "TCS" in symbols


def test_backtest_returns_checkpoints_with_caveat(client, db_session):
    _login_admin(client, db_session)
    _seed_company_with_long_history(db_session, "TCS", "Tata Consultancy Services Ltd")

    proposed = _valid_config_payload(rsi_period=21)
    response = client.post("/api/admin/strategies/backtest", json={"config": proposed, "symbols": ["TCS"]})

    assert response.status_code == 200
    body = response.json()
    assert body["caveat"]
    assert len(body["checkpoints"]) > 0
    checkpoint = body["checkpoints"][0]
    assert checkpoint["symbol"] == "TCS"
    assert checkpoint["active_score"] is not None
    assert checkpoint["proposed_score"] is not None


def test_backtest_skips_companies_with_too_little_history(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")  # only 10 days

    response = client.post(
        "/api/admin/strategies/backtest", json={"config": _valid_config_payload(), "symbols": ["TCS"]}
    )

    assert response.status_code == 200
    assert response.json()["checkpoints"] == []
