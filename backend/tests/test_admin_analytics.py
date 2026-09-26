from app.models.user import UserRole
from tests.test_research import _create_user, _seed_company


def _login_admin(client, db_session):
    admin = _create_user(db_session, email="admin@example.com", password="correct-password")
    admin.role = UserRole.admin
    db_session.commit()
    client.post("/api/auth/login", json={"email": admin.email, "password": "correct-password"})
    return admin


def test_analytics_requires_admin(client, db_session):
    _create_user(db_session, email="user@example.com")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    response = client.get("/api/admin/analytics")
    assert response.status_code == 403


def test_analytics_counts_users_sessions_and_messages(client, db_session):
    _login_admin(client, db_session)
    _create_user(db_session, email="user2@example.com")
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    client.post("/api/research/chat", json={"message": "Analyse TCS"})

    response = client.get("/api/admin/analytics")
    assert response.status_code == 200
    body = response.json()

    assert body["total_users"] == 2
    assert body["active_users"] == 2
    assert body["total_research_sessions"] == 1
    assert body["total_research_messages"] == 2


def test_analytics_most_researched_reflects_mention_frequency(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "INFY", "Infosys Ltd")

    client.post("/api/research/chat", json={"message": "Analyse TCS"})
    client.post("/api/research/chat", json={"message": "Explain TCS financial performance"})
    client.post("/api/research/chat", json={"message": "Analyse Infosys"})

    response = client.get("/api/admin/analytics")
    most_researched = response.json()["most_researched"]

    assert most_researched[0]["symbol"] == "TCS"
    assert most_researched[0]["mention_count"] == 2
    assert most_researched[1]["symbol"] == "INFY"
    assert most_researched[1]["mention_count"] == 1


def test_analytics_does_not_confuse_shared_word_companies(client, db_session):
    """Regression guard: since this reuses find_mentioned_companies, it should
    inherit the same fix as the chat matcher (see test_research.py)."""
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    client.post("/api/research/chat", json={"message": "What are the weaknesses of Tata Motors?"})

    response = client.get("/api/admin/analytics")
    most_researched = {row["symbol"]: row["mention_count"] for row in response.json()["most_researched"]}

    assert most_researched.get("TATAMOTORS") == 1
    assert "TCS" not in most_researched
