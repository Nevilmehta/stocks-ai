from datetime import date

from app.services.historical_price_lookup import extract_date_from_message, is_price_lookup_question

TODAY = date(2026, 9, 26)


def test_is_price_lookup_question_true_for_price_phrasing():
    assert is_price_lookup_question("what was the tcs closing price on 24th september")
    assert is_price_lookup_question("give me reliance's open on that day")


def test_is_price_lookup_question_false_for_ordinary_analysis():
    assert not is_price_lookup_question("analyse tcs")
    assert not is_price_lookup_question("compare tcs and infosys")
    assert not is_price_lookup_question("is hdfc bank valuation expensive")


def test_extract_date_from_message_absolute_date():
    assert extract_date_from_message("what was the tcs closing price on 24th september", TODAY) == date(2026, 9, 24)


def test_extract_date_from_message_with_explicit_year():
    assert extract_date_from_message("tcs price on Sept 24 2025", TODAY) == date(2025, 9, 24)


def test_extract_date_from_message_iso_format():
    assert extract_date_from_message("reliance close on 2026-01-15", TODAY) == date(2026, 1, 15)


def test_extract_date_from_message_yesterday():
    assert extract_date_from_message("what was tcs price yesterday", TODAY) == date(2026, 9, 25)


def test_extract_date_from_message_today():
    assert extract_date_from_message("tcs price today", TODAY) == TODAY


def test_extract_date_from_message_returns_none_when_no_date():
    assert extract_date_from_message("analyse tcs", TODAY) is None
    assert extract_date_from_message("compare tcs and infosys", TODAY) is None
