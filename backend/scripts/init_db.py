"""Create all database tables. Run once after PostgreSQL is up and reachable.

Usage (from backend/, with venv activated):
    python scripts/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: F401  (import registers models on Base.metadata)
from app.database import Base, engine


def main() -> None:
    print(f"Creating tables on: {engine.url.render_as_string(hide_password=True)}")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created (or already existed):")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    main()
