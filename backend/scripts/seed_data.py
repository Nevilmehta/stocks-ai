"""Seed development-only demo accounts and the mock company universe.

Usage (from backend/, with venv activated):
    python scripts/seed_data.py

Admin/demo passwords come from the SEED_ADMIN_PASSWORD / SEED_DEMO_PASSWORD
environment variables. If unset, a random password is generated and printed
ONCE - it is never stored in code or committed anywhere. These accounts are
for local development only; do not reuse these credentials in production.
"""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

from dotenv import load_dotenv

from app.database import Base, SessionLocal, engine
from app.models.company import Company
from app.models.user import User, UserRole
from app.seed.companies import DEMO_COMPANIES
from app.security import hash_password

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _resolve_password(env_var: str) -> tuple[str, bool]:
    value = os.getenv(env_var)
    if value:
        return value, False
    return secrets.token_urlsafe(12), True


def seed_users(db) -> None:
    admin_password, admin_generated = _resolve_password("SEED_ADMIN_PASSWORD")
    demo_password, demo_generated = _resolve_password("SEED_DEMO_PASSWORD")

    seed_users_spec = [
        ("admin@example.com", "Admin User", UserRole.admin, admin_password, admin_generated),
        ("demo@example.com", "Demo User", UserRole.user, demo_password, demo_generated),
    ]

    for email, display_name, role, password, generated in seed_users_spec:
        existing = db.query(User).filter(User.email == email).first()
        if existing is not None:
            print(f"[skip] {email} already exists")
            continue

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        note = " (generated - save this now)" if generated else ""
        print(f"[created] {email} / role={role.value} / password={password}{note}")

    db.commit()


def seed_companies(db) -> None:
    for company_data in DEMO_COMPANIES:
        existing = db.query(Company).filter(Company.symbol == company_data["symbol"]).first()
        if existing is not None:
            print(f"[skip] {company_data['symbol']} already exists")
            continue
        db.add(Company(**company_data))
        print(f"[created] {company_data['symbol']} - {company_data['name']}")
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("== Seeding development users (DEV ONLY, not for production) ==")
        seed_users(db)
        print("\n== Seeding demo companies (DEMO DATA, not real market data) ==")
        seed_companies(db)
    finally:
        db.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
