from datetime import date, timedelta

from app.models.price_history import PriceHistory
from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def _add_declining_day(db_session, company, drop_to: float):
    """_seed_company's last price row is an advance; append one more, lower
    row so this company shows up as a decliner/loser instead."""
    db_session.add(
        PriceHistory(
            company_id=company.id,
            date=date.today() + timedelta(days=1),
            open=drop_to,
            high=drop_to + 1,
            low=drop_to - 1,
            close=drop_to,
            volume=100000,
        )
    )
    db_session.commit()


def test_overview_requires_authentication(client):
    response = client.get("/api/stocks/overview")
    assert response.status_code == 401


def test_overview_counts_companies_and_sectors(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = client.get("/api/stocks/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["total_companies"] == 2
    assert body["sectors"] == 2
    breakdown = {row["sector"]: row["count"] for row in body["sector_breakdown"]}
    assert breakdown == {"Information Technology": 1, "Automobile": 1}


def test_overview_splits_advancers_and_decliners(client, db_session):
    _login(client, db_session)
    gainer = _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    loser = _seed_company(db_session, "INFY", "Infosys Ltd")
    _add_declining_day(db_session, loser, drop_to=50)

    response = client.get("/api/stocks/overview")
    body = response.json()

    assert body["advancers"] == 1
    assert body["decliners"] == 1

    gainer_symbols = {m["symbol"] for m in body["top_gainers"]}
    loser_symbols = {m["symbol"] for m in body["top_losers"]}
    assert gainer.symbol in gainer_symbols
    assert loser.symbol in loser_symbols
    assert all(m["change_percent"] > 0 for m in body["top_gainers"])
    assert all(m["change_percent"] < 0 for m in body["top_losers"])


def test_overview_top_losers_ordered_worst_first(client, db_session):
    _login(client, db_session)
    mild_loser = _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _add_declining_day(db_session, mild_loser, drop_to=105)  # small drop from 109.5
    steep_loser = _seed_company(db_session, "INFY", "Infosys Ltd")
    _add_declining_day(db_session, steep_loser, drop_to=10)  # steep drop from 109.5

    response = client.get("/api/stocks/overview")
    top_losers = response.json()["top_losers"]

    assert [m["symbol"] for m in top_losers] == [steep_loser.symbol, mild_loser.symbol]
    assert top_losers[0]["change_percent"] < top_losers[1]["change_percent"]


def test_overview_caps_movers_at_five(client, db_session):
    _login(client, db_session)
    for i in range(7):
        _seed_company(db_session, f"CO{i}", f"Company {i} Ltd", sector="Energy")

    response = client.get("/api/stocks/overview")
    body = response.json()

    assert body["total_companies"] == 7
    assert len(body["top_gainers"]) <= 5
