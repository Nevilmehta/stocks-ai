from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def test_peers_requires_authentication(client):
    response = client.get("/api/stocks/TCS/peers")
    assert response.status_code == 401


def test_peers_404s_for_unknown_company(client, db_session):
    _login(client, db_session)
    response = client.get("/api/stocks/NOTREAL/peers")
    assert response.status_code == 404


def test_peers_returns_same_sector_companies_excluding_self(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")
    _seed_company(db_session, "INFY", "Infosys Ltd", sector="Information Technology")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = client.get("/api/stocks/TCS/peers")
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()}
    assert symbols == {"INFY"}


def test_peers_empty_for_unclassified_sector(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Unclassified")
    _seed_company(db_session, "INFY", "Infosys Ltd", sector="Unclassified")

    response = client.get("/api/stocks/TCS/peers")
    assert response.status_code == 200
    assert response.json() == []
