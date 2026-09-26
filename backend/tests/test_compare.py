from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def test_compare_requires_authentication(client):
    response = client.post("/api/compare", json={"symbols": ["TCS", "INFY"]})
    assert response.status_code == 401


def test_compare_requires_at_least_two_symbols(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = client.post("/api/compare", json={"symbols": ["TCS"]})
    assert response.status_code == 400


def test_compare_rejects_more_than_three_symbols(client, db_session):
    _login(client, db_session)
    for symbol, name in [("A", "Company A Ltd"), ("B", "Company B Ltd"), ("C", "Company C Ltd"), ("D", "Company D Ltd")]:
        _seed_company(db_session, symbol, name)

    response = client.post("/api/compare", json={"symbols": ["A", "B", "C", "D"]})
    assert response.status_code == 400


def test_compare_unknown_symbol_returns_404(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = client.post("/api/compare", json={"symbols": ["TCS", "NOPE"]})
    assert response.status_code == 404


def test_compare_two_companies_returns_both_rows(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "INFY", "Infosys Ltd")

    response = client.post("/api/compare", json={"symbols": ["TCS", "INFY"]})
    assert response.status_code == 200
    rows = response.json()["rows"]
    symbols = {row["symbol"] for row in rows}
    assert symbols == {"TCS", "INFY"}
    for row in rows:
        assert row["ai_score"] is not None
        assert len(row["history"]) > 0


def test_compare_ai_returns_grounded_text_without_buy_sell_language(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "INFY", "Infosys Ltd")

    response = client.post("/api/compare/ai", json={"symbols": ["TCS", "INFY"]})
    assert response.status_code == 200
    text = response.json()["text"]
    assert "TCS" in text
    assert "INFY" in text
    lowered = text.lower()
    for phrase in ("strong buy", "buy now", "sell now"):
        assert phrase not in lowered
