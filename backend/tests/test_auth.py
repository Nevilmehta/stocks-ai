from app.models.user import User, UserRole
from app.routers import auth as auth_router
from app.security import hash_password


def _create_user(db_session, email, password, role=UserRole.user, is_active=True):
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=email.split("@")[0],
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success_sets_cookie(client, db_session):
    _create_user(db_session, "user@example.com", "correct-password")

    response = client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "correct-password"}
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "user@example.com"
    assert "access_token" in response.cookies


def test_login_wrong_password_rejected(client, db_session):
    _create_user(db_session, "user@example.com", "correct-password")

    response = client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_deactivated_user_rejected(client, db_session):
    _create_user(db_session, "inactive@example.com", "correct-password", is_active=False)

    response = client.post(
        "/api/auth/login", json={"email": "inactive@example.com", "password": "correct-password"}
    )

    assert response.status_code == 403


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_after_login(client, db_session):
    _create_user(db_session, "user@example.com", "correct-password")

    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_registration_disabled_when_flag_off(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "allow_registration", False)

    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "some-password", "display_name": "New User"},
    )
    assert response.status_code == 403


def test_registration_success_when_enabled(client, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "allow_registration", True)

    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "some-password", "display_name": "New User"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "new@example.com"
    assert "access_token" in response.cookies


def test_registration_duplicate_email_rejected(client, db_session, monkeypatch):
    monkeypatch.setattr(auth_router.settings, "allow_registration", True)
    _create_user(db_session, "existing@example.com", "correct-password")

    response = client.post(
        "/api/auth/register",
        json={"email": "existing@example.com", "password": "some-password", "display_name": "Dup User"},
    )

    assert response.status_code == 409


def test_admin_route_rejects_regular_user(client, db_session):
    _create_user(db_session, "user@example.com", "correct-password", role=UserRole.user)
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    response = client.get("/api/admin/users")
    assert response.status_code == 403


def test_admin_route_allows_admin_user(client, db_session):
    _create_user(db_session, "admin@example.com", "correct-password", role=UserRole.admin)
    client.post("/api/auth/login", json={"email": "admin@example.com", "password": "correct-password"})

    response = client.get("/api/admin/users")
    assert response.status_code == 200
    assert len(response.json()) == 1
