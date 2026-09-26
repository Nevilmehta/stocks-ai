from app.services.email_service import send_email, send_welcome_email


def test_send_email_skips_when_smtp_not_configured():
    assert send_email("someone@example.com", "Subject", "Body") is False


def test_send_welcome_email_skips_when_smtp_not_configured():
    assert send_welcome_email("Jane Doe", "jane@example.com") is False
