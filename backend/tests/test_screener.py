from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def test_screener_requires_authentication(client):
    response = client.get("/api/screener")
    assert response.status_code == 401


def test_screener_returns_all_companies_with_no_filters(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = client.get("/api/screener")
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()}
    assert symbols == {"TCS", "TATAMOTORS"}


def test_screener_filters_by_sector(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = client.get("/api/screener", params={"sector": "Automobile"})
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()}
    assert symbols == {"TATAMOTORS"}


def test_screener_filters_by_roe_min(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")  # seeded roe=18

    matching = client.get("/api/screener", params={"roe_min": 10})
    assert len(matching.json()) == 1

    none_match = client.get("/api/screener", params={"roe_min": 50})
    assert none_match.json() == []


def test_screener_results_are_sorted_by_ai_score_desc(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "INFY", "Infosys Ltd")

    response = client.get("/api/screener")
    scores = [row["ai_score"] for row in response.json()]
    assert scores == sorted(scores, reverse=True)


def test_screener_combines_multiple_filters(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = client.get(
        "/api/screener",
        params={"roe_min": 10, "debt_to_equity_max": 2, "revenue_growth_min": 5},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
