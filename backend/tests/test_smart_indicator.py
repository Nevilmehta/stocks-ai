from datetime import date, timedelta

from app.models.company import Company
from app.models.price_history import PriceHistory
from app.models.strategy import ResearchStrategy
from app.schemas.strategy import DEFAULT_STRATEGY_CONFIG
from tests.test_research import _create_user, _seed_company


def _login(client, db_session, email="user@example.com"):
    _create_user(db_session, email=email)
    client.post("/api/auth/login", json={"email": email, "password": "correct-password"})


def _activate_strategy(db_session, **overrides) -> None:
    config = DEFAULT_STRATEGY_CONFIG.model_dump()
    config.update(overrides)
    db_session.query(ResearchStrategy).update({"is_active": False})
    db_session.add(ResearchStrategy(name="test", config=config, is_active=True))
    db_session.commit()


def _seed_company_with_trend(
    db_session, symbol: str, name: str, daily_change: float, days: int = 400, start_price: float = 300.0
):
    """A standalone company (NOT via _seed_company, which would also add its
    own flat 10-day seed near "today" - overlapping/gapping against a
    deliberately-trending series would corrupt the very latest technicals,
    which is exactly what these tests need to be clean) with a continuous
    daily-compounding trend running right up to yesterday."""
    company = Company(
        symbol=symbol,
        name=name,
        exchange="NSE",
        sector="Information Technology",
        industry="IT Services & Consulting",
        description=f"{name} - test fixture.",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    start = date.today() - timedelta(days=days)
    price = start_price
    for i in range(days):
        price *= daily_change
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


def test_smart_indicator_requires_authentication(client):
    response = client.get("/api/smart-indicator")
    assert response.status_code == 401


def test_smart_indicator_returns_rows_with_signal_fields(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")

    response = client.get("/api/smart-indicator")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["symbol"] == "TCS"
    assert row["signal"] in {"buy", "sell", "neutral"}
    assert isinstance(row["signal_reasons"], list)
    assert "swing_structure" in row
    assert "volume" in row
    assert "return_1d" in row
    assert "return_1w" in row
    assert "return_1m" in row
    # "overall" is the default_smart_indicator out of the box - not asserting
    # a specific indicator_value/label here since _seed_company's 10-day
    # history is too thin for most indicators to compute at all (see the
    # dedicated test_overall_score_* tests below for real computed values).
    assert row["indicator"] == "overall"
    assert "indicator_label" in row


def test_overall_score_combines_enabled_indicators_with_real_data(client, db_session):
    _login(client, db_session)
    _seed_company_with_trend(db_session, "TCS", "Tata Consultancy Services Ltd", daily_change=1.001)

    response = client.get("/api/smart-indicator", params={"indicator": "overall"})
    assert response.status_code == 200
    row = response.json()[0]
    assert row["indicator_value"] is not None
    # Default config has 5 vote-eligible indicators enabled (RSI/SMA/EMA/MACD/
    # Bollinger) - Fibonacci never votes, see _overall_score's docstring.
    assert row["indicator_label"] == "Overall (5 indicators)"


def test_overall_score_only_counts_enabled_indicators(client, db_session):
    _login(client, db_session)
    _seed_company_with_trend(db_session, "TCS", "Tata Consultancy Services Ltd", daily_change=1.001)
    _activate_strategy(db_session, enable_sma=False, enable_ema=False, enable_bollinger=False)

    response = client.get("/api/smart-indicator", params={"indicator": "overall"})
    assert response.status_code == 200
    row = response.json()[0]
    # Only RSI + MACD left enabled.
    assert row["indicator_label"] == "Overall (2 indicators)"


def test_overall_score_sorts_highest_first(client, db_session):
    _login(client, db_session)
    # A steady uptrend should score higher overall than a steady downtrend.
    _seed_company_with_trend(db_session, "UPCO", "Up Co", daily_change=1.003)
    _seed_company_with_trend(db_session, "DOWNCO", "Down Co", daily_change=0.997)

    response = client.get("/api/smart-indicator", params={"indicator": "overall"})
    assert response.status_code == 200
    rows = response.json()
    by_symbol = {r["symbol"]: r["indicator_value"] for r in rows}
    assert by_symbol["UPCO"] > by_symbol["DOWNCO"]
    symbols = [r["symbol"] for r in rows]
    assert symbols.index("UPCO") < symbols.index("DOWNCO")


def test_smart_indicator_filters_by_sector(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd", sector="Information Technology")
    _seed_company(db_session, "TATAMOTORS", "Tata Motors Ltd", sector="Automobile")

    response = client.get("/api/smart-indicator", params={"sector": "Automobile"})
    assert response.status_code == 200
    symbols = {row["symbol"] for row in response.json()}
    assert symbols == {"TATAMOTORS"}


def test_smart_indicator_filters_by_signal(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    all_rows = client.get("/api/smart-indicator").json()
    actual_signal = all_rows[0]["signal"]

    matching = client.get("/api/smart-indicator", params={"signal": actual_signal})
    assert len(matching.json()) == 1

    other_signal = next(s for s in ("buy", "sell", "neutral") if s != actual_signal)
    none_match = client.get("/api/smart-indicator", params={"signal": other_signal})
    assert none_match.json() == []


def test_smart_indicator_indicator_param_switches_value_and_label(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    response = client.get("/api/smart-indicator", params={"indicator": "fibonacci"})
    assert response.status_code == 200
    row = response.json()[0]
    assert row["indicator"] == "fibonacci"
    assert row["indicator_label"] == "Fib. distance %"


def test_smart_indicator_indicator_label_reflects_configured_period(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _activate_strategy(db_session, rsi_period=9, sma_medium=30)

    rsi_row = client.get("/api/smart-indicator", params={"indicator": "rsi"}).json()[0]
    assert rsi_row["indicator_label"] == "RSI (9)"

    sma_row = client.get("/api/smart-indicator", params={"indicator": "sma"}).json()[0]
    assert sma_row["indicator_label"] == "vs SMA30 %"


def test_smart_indicator_rejects_explicitly_disabled_indicator(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _activate_strategy(db_session, enable_fibonacci=False)

    response = client.get("/api/smart-indicator", params={"indicator": "fibonacci"})
    assert response.status_code == 400


def test_smart_indicator_overall_is_never_rejected(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    _activate_strategy(
        db_session,
        enable_sma=False,
        enable_ema=False,
        enable_rsi=False,
        enable_macd=False,
        enable_bollinger=False,
        enable_fibonacci=False,
    )

    response = client.get("/api/smart-indicator", params={"indicator": "overall"})
    assert response.status_code == 200


def test_smart_indicator_falls_back_to_overall_when_default_indicator_is_disabled(client, db_session):
    _login(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")
    # default_smart_indicator explicitly set to a now-disabled indicator -
    # should fall back to "overall" (always valid), not 400, since no
    # explicit ?indicator= was requested.
    _activate_strategy(db_session, default_smart_indicator="rsi", enable_rsi=False)

    response = client.get("/api/smart-indicator")
    assert response.status_code == 200
    assert response.json()[0]["indicator"] == "overall"


def test_smart_indicator_meta_always_includes_overall_plus_enabled_indicators(client, db_session):
    _login(client, db_session)
    _activate_strategy(db_session, enable_fibonacci=False, enable_bollinger=False)

    response = client.get("/api/smart-indicator/meta")
    assert response.status_code == 200
    body = response.json()
    keys = {opt["key"] for opt in body["available_indicators"]}
    assert keys == {"overall", "sma", "ema", "rsi", "macd"}
    assert body["default_indicator"] == "overall"


def test_smart_indicator_meta_only_overall_when_everything_else_disabled(client, db_session):
    _login(client, db_session)
    _activate_strategy(
        db_session,
        enable_sma=False,
        enable_ema=False,
        enable_rsi=False,
        enable_macd=False,
        enable_bollinger=False,
        enable_fibonacci=False,
    )

    response = client.get("/api/smart-indicator/meta")
    assert response.status_code == 200
    body = response.json()
    assert [opt["key"] for opt in body["available_indicators"]] == ["overall"]
    assert body["default_indicator"] == "overall"
