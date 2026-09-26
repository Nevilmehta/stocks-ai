"""Minimal SMTP email sending. Not a provider abstraction like AI/market data
since this app only ever needs "send a plain email" - no swappable backends
planned. If SMTP isn't configured (no host/username/password in .env), sends
are skipped and logged instead of raising, so features that trigger an email
(registration, admin-created users) still work without email set up yet.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.config import get_settings

logger = logging.getLogger("stockai.email")


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    settings = get_settings()

    if not settings.is_smtp_configured:
        logger.info("SMTP not configured - skipping email to %s: %s", to_email, subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Reply-To"] = settings.smtp_from_email
    # Explicit Date/Message-ID headers - some spam filters weight their
    # absence, and smtplib doesn't add them automatically.
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=settings.smtp_from_email.split("@")[-1])
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_welcome_email(display_name: str, email: str) -> bool:
    settings = get_settings()
    first_name = display_name.split(" ")[0] if display_name else "there"
    product = settings.smtp_from_name
    login_url = f"{settings.frontend_url}/login"

    subject = f"Welcome to {product} - your account is ready"

    body = (
        f"Hi {first_name},\n\n"
        f"Your {product} account has been created for {email}.\n\n"
        f"{product} gives you financials, technical indicators, and AI-powered research for Indian "
        "stocks, all grounded in real market data - never invented numbers, never buy/sell advice.\n\n"
        f"Sign in here: {login_url}\n\n"
        "This is a private beta - please don't share your login with anyone else.\n\n"
        f"- The {product} Team"
    )

    html_body = f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;max-width:480px;width:100%;">
            <tr>
              <td style="background-color:#0f172a;padding:24px 32px;">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="width:32px;height:32px;border-radius:8px;background-color:#ffffff;" align="center" valign="middle">
                      <!-- Same mark as the app's navbar: lucide "chart-line" icon (ISC licensed) -->
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:block;">
                        <path d="M3 3v16a2 2 0 0 0 2 2h16" />
                        <path d="m19 9-5 5-4-4-3 3" />
                      </svg>
                    </td>
                    <td style="padding-left:10px;" valign="middle">
                      <span style="color:#ffffff;font-size:18px;font-weight:700;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">{product}</span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h1 style="margin:0 0 16px;font-size:20px;color:#0f172a;">Welcome, {first_name} 👋</h1>
                <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#3f3f46;">
                  Your {product} account has been created for <strong>{email}</strong>.
                </p>
                <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#3f3f46;">
                  {product} gives you financials, technical indicators, and AI-powered research for
                  Indian stocks, all grounded in real market data - never invented numbers, never
                  buy/sell advice.
                </p>
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="border-radius:8px;background-color:#0f172a;">
                      <a href="{login_url}" style="display:inline-block;padding:12px 24px;font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;">
                        Sign in to {product}
                      </a>
                    </td>
                  </tr>
                </table>
                <p style="margin:28px 0 0;font-size:12px;line-height:1.5;color:#a1a1aa;">
                  This is a private beta - please don't share your login with anyone else.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    return send_email(email, subject, body, html_body=html_body)
