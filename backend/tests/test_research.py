from datetime import date, timedelta

import pytest

from app.models.company import Company
from app.models.financials import CompanyFinancials, FinancialRatios, PeriodType
from app.models.price_history import PriceHistory
from app.models.user import User, UserRole
from app.security import hash_password


def _create_user(db_session, email="user@example.com", password="correct-password"):
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Test User",
        role=UserRole.user,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_company(db_session, symbol: str, name: str, sector: str = "Information Technology") -> Company:
    company = Company(
        symbol=symbol,
        name=name,
        exchange="NSE",
        sector=sector,
        industry="IT Services & Consulting",
        description=f"{name} is a demo company used for tests.",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    today = date.today()
    for i in range(10):
        db_session.add(
            PriceHistory(
                company_id=company.id,
                date=today - timedelta(days=(10 - i)),
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100.5 + i,
                volume=100000,
            )
        )

    db_session.add(
        CompanyFinancials(
            company_id=company.id,
            period_type=PeriodType.annual,
            period_label="FY2026",
            fiscal_year=2026,
            sequence=0,
            revenue=10000,
            net_profit=1500,
            operating_profit=2000,
            eps=20,
            operating_cash_flow=1600,
            total_debt=5000,
        )
    )
    db_session.add(
        FinancialRatios(
            company_id=company.id,
            period_type=PeriodType.annual,
            period_label="FY2026",
            fiscal_year=2026,
            sequence=0,
            pe_ratio=20,
            pb_ratio=3,
            roe=18,
            roce=20,
            debt_to_equity=0.8,
            revenue_growth=12,
            profit_growth=15,
            net_margin=15,
            market_cap=100000,
        )
    )
    db_session.commit()
    return company


@pytest.fixture
def logged_in_client(client, db_session):
    user = _create_user(db_session)
    client.post("/api/auth/login", json={"email": user.email, "password": "correct-password"})
    return client


def test_analyse_requires_authentication(client):
    response = client.post("/api/research/analyse", json={"symbol": "TCS"})
    assert response.status_code == 401


def test_analyse_unknown_symbol_returns_404(logged_in_client):
    response = logged_in_client.post("/api/research/analyse", json={"symbol": "NOPE"})
    assert response.status_code == 404


def test_analyse_returns_grounded_analysis_and_saves_history(logged_in_client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = logged_in_client.post("/api/research/analyse", json={"symbol": "TCS"})
    assert response.status_code == 200
    body = response.json()

    assert body["symbol"] == "TCS"
    assert body["provider"] == "mock"
    assert "18.0" in body["profitability"] or "18" in body["profitability"]
    for field in ("summary", "financial_health", "growth", "profitability", "valuation", "technical_picture", "conclusion", "disclaimer"):
        assert body[field]
    assert isinstance(body["strengths"], list) and body["strengths"]
    assert isinstance(body["risks"], list) and body["risks"]

    forbidden = ["strong buy", "buy now", "sell now", "target price"]
    full_text = " ".join([body["summary"], body["conclusion"]] + body["strengths"] + body["risks"]).lower()
    for phrase in forbidden:
        assert phrase not in full_text

    history = logged_in_client.get("/api/research/history")
    assert history.status_code == 200
    sessions = history.json()
    assert len(sessions) == 1
    assert "TCS" in sessions[0]["title"]


def test_chat_without_company_mention_gives_generic_guidance(logged_in_client):
    response = logged_in_client.post("/api/research/chat", json={"message": "hello there"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"
    assert "mention" in body["messages"][1]["content"].lower()


def test_chat_market_wide_question_uses_real_overview_data(logged_in_client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = logged_in_client.post("/api/research/chat", json={"message": "What are the top gainers today?"})
    assert response.status_code == 200
    body = response.json()
    content = body["messages"][1]["content"]
    assert "TCS" in content
    assert "mention" not in content.lower()  # shouldn't hit the generic no-company fallback


def test_chat_last_updated_question_states_a_real_date(logged_in_client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = logged_in_client.post("/api/research/chat", json={"message": "When was this data last updated?"})
    assert response.status_code == 200
    content = response.json()["messages"][1]["content"]
    # _seed_company's most recent PriceHistory row is yesterday, not today.
    assert (date.today() - timedelta(days=1)).isoformat() in content


def test_chat_with_single_company_mention_grounds_answer(logged_in_client, db_session):
    _seed_company(db_session, "INFY", "Infosys Ltd")

    response = logged_in_client.post("/api/research/chat", json={"message": "Analyse Infosys please"})
    assert response.status_code == 200
    body = response.json()
    assistant_message = body["messages"][1]["content"]
    assert "INFY" in assistant_message or "Infosys" in assistant_message


def test_chat_does_not_confuse_companies_sharing_a_common_name_word(logged_in_client, db_session):
    """Regression test: "Tata" is shared by Tata Motors and Tata Consultancy
    Services, so a question naming only "Tata Motors" must not also match TCS
    and silently turn into a comparison instead of a single-company answer."""
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = logged_in_client.post(
        "/api/research/chat", json={"message": "What are the weaknesses of Tata Motors?"}
    )
    assert response.status_code == 200
    assistant_message = response.json()["messages"][1]["content"]

    assert "TATAMOTORS" in assistant_message
    assert "TCS" not in assistant_message
    assert "Comparing" not in assistant_message


def test_chat_with_two_companies_compares_them(logged_in_client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _seed_company(db_session, "INFY", "Infosys Ltd")

    response = logged_in_client.post("/api/research/chat", json={"message": "Compare TCS and Infosys"})
    assert response.status_code == 200
    body = response.json()
    assistant_message = body["messages"][1]["content"]
    assert "TCS" in assistant_message
    assert "INFY" in assistant_message


def test_chat_continues_existing_session(logged_in_client, db_session):
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    first = logged_in_client.post("/api/research/chat", json={"message": "Analyse TCS"})
    session_id = first.json()["id"]

    second = logged_in_client.post(
        "/api/research/chat", json={"message": "What about the risks?", "session_id": session_id}
    )
    assert second.status_code == 200
    body = second.json()
    assert body["id"] == session_id
    assert len(body["messages"]) == 4


def test_history_is_scoped_to_the_logged_in_user(client, db_session):
    user_a = _create_user(db_session, email="a@example.com")
    user_b = _create_user(db_session, email="b@example.com")
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    client.post("/api/auth/login", json={"email": user_a.email, "password": "correct-password"})
    client.post("/api/research/chat", json={"message": "Analyse TCS"})
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"email": user_b.email, "password": "correct-password"})
    history = client.get("/api/research/history")
    assert history.json() == []


def test_history_session_detail_not_found_for_other_users_session(client, db_session):
    user_a = _create_user(db_session, email="a@example.com")
    user_b = _create_user(db_session, email="b@example.com")
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    client.post("/api/auth/login", json={"email": user_a.email, "password": "correct-password"})
    chat_response = client.post("/api/research/chat", json={"message": "Analyse TCS"})
    session_id = chat_response.json()["id"]
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"email": user_b.email, "password": "correct-password"})
    response = client.get(f"/api/research/history/{session_id}")
    assert response.status_code == 404


def test_chat_rejects_empty_message(logged_in_client):
    response = logged_in_client.post("/api/research/chat", json={"message": "   "})
    assert response.status_code == 400
