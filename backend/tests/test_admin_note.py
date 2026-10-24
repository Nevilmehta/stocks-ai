from tests.test_admin_analytics import _login_admin
from tests.test_research import _create_user


def _login_user(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def test_dashboard_note_endpoints_require_admin(client, db_session):
    _login_user(client, db_session)

    assert client.post("/api/admin/dashboard-note", json={"message": "buy X"}).status_code == 403
    assert client.get("/api/admin/dashboard-note/history").status_code == 403


def test_customer_endpoint_returns_null_when_no_note_posted(client, db_session):
    _login_user(client, db_session)

    response = client.get("/api/dashboard-note")
    assert response.status_code == 200
    assert response.json() is None


def test_admin_posts_note_and_customer_sees_it(client, db_session):
    _login_admin(client, db_session)
    create = client.post("/api/admin/dashboard-note", json={"message": "Consider TCS, avoid XYZ."})
    assert create.status_code == 201
    assert create.json()["is_active"] is True

    _login_user(client, db_session)
    response = client.get("/api/dashboard-note")
    assert response.status_code == 200
    assert response.json()["message"] == "Consider TCS, avoid XYZ."


def test_posting_a_new_note_deactivates_the_previous_one(client, db_session):
    _login_admin(client, db_session)
    client.post("/api/admin/dashboard-note", json={"message": "first note"})
    client.post("/api/admin/dashboard-note", json={"message": "second note"})

    response = client.get("/api/dashboard-note")
    assert response.json()["message"] == "second note"

    history = client.get("/api/admin/dashboard-note/history").json()
    assert len(history) == 2
    active_count = sum(1 for n in history if n["is_active"])
    assert active_count == 1


def test_empty_message_clears_the_note(client, db_session):
    _login_admin(client, db_session)
    client.post("/api/admin/dashboard-note", json={"message": "a note"})
    client.post("/api/admin/dashboard-note", json={"message": ""})

    response = client.get("/api/dashboard-note")
    assert response.status_code == 200
    assert response.json() is None
