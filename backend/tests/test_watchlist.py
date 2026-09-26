from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    user = _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})
    return user


def test_watchlist_requires_authentication(client):
    response = client.get("/api/watchlist")
    assert response.status_code == 401


def test_watchlist_starts_empty(client, db_session):
    _login(client, db_session)
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    assert response.json() == []


def test_add_unknown_symbol_returns_404(client, db_session):
    _login(client, db_session)
    response = client.post("/api/watchlist", json={"symbol": "NOPE"})
    assert response.status_code == 404


def test_add_and_list_watchlist_item(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    add_response = client.post("/api/watchlist", json={"symbol": "tcs"})
    assert add_response.status_code == 201
    body = add_response.json()
    assert body["symbol"] == "TCS"
    assert body["latest_price"] is not None
    assert body["ai_score"] is not None

    list_response = client.get("/api/watchlist")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["symbol"] == "TCS"


def test_adding_same_symbol_twice_is_idempotent(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    client.post("/api/watchlist", json={"symbol": "TCS"})
    client.post("/api/watchlist", json={"symbol": "TCS"})

    items = client.get("/api/watchlist").json()
    assert len(items) == 1


def test_remove_from_watchlist(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    client.post("/api/watchlist", json={"symbol": "TCS"})
    remove_response = client.delete("/api/watchlist/TCS")
    assert remove_response.status_code == 204

    items = client.get("/api/watchlist").json()
    assert items == []


def test_watchlist_is_scoped_per_user(client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    _login(client, db_session, email="a@example.com")
    client.post("/api/watchlist", json={"symbol": "TCS"})
    client.post("/api/auth/logout")

    _login(client, db_session, email="b@example.com")
    items = client.get("/api/watchlist").json()
    assert items == []
