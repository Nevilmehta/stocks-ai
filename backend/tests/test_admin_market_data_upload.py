import io
import zipfile
from datetime import date

from app.models.company import Company
from app.models.price_history import PriceHistory
from app.models.sync_log import MarketDataSyncLog
from tests.test_admin_analytics import _login_admin
from tests.test_nse_bhavcopy import CURRENT_CSV, LEGACY_CSV
from tests.test_research import _create_user, _seed_company


def _zip_bytes(internal_filename: str, csv_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(internal_filename, csv_text)
    return buffer.getvalue()


def test_upload_requires_admin(client, db_session):
    _create_user(db_session, email="user@example.com")
    client.post("/api/auth/login", json={"email": "user@example.com", "password": "correct-password"})

    zip_data = _zip_bytes("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv", CURRENT_CSV)
    response = client.post(
        "/api/admin/market-data/upload",
        files={"files": ("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 403


def test_upload_current_format_upserts_price_history(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    zip_data = _zip_bytes("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv", CURRENT_CSV)
    response = client.post(
        "/api/admin/market-data/upload",
        files={"files": ("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip", zip_data, "application/zip")},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["error"] is None
    assert result["trade_date"] == "2025-12-22"
    assert result["rows_synced"] == 1

    company = db_session.query(Company).filter(Company.symbol == "TCS").first()
    row = (
        db_session.query(PriceHistory)
        .filter(PriceHistory.company_id == company.id, PriceHistory.date == date(2025, 12, 22))
        .first()
    )
    assert row is not None
    assert float(row.close) == 3324.90

    log_entry = db_session.query(MarketDataSyncLog).filter(MarketDataSyncLog.trade_date == date(2025, 12, 22)).first()
    assert log_entry is not None
    assert log_entry.status.value == "success"
    assert log_entry.source.value == "manual_upload"


def test_upload_legacy_format_upserts_price_history(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    zip_data = _zip_bytes("cm02JAN2024bhav.csv", LEGACY_CSV)
    response = client.post(
        "/api/admin/market-data/upload",
        files={"files": ("cm02JAN2024bhav.csv.zip", zip_data, "application/zip")},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["error"] is None
    assert result["trade_date"] == "2024-01-02"
    assert result["rows_synced"] == 1


def test_upload_multiple_files_reports_each_independently(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    good_zip = _zip_bytes("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv", CURRENT_CSV)
    bad_zip = b"not a real zip file"

    response = client.post(
        "/api/admin/market-data/upload",
        files=[
            ("files", ("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip", good_zip, "application/zip")),
            ("files", ("corrupt.zip", bad_zip, "application/zip")),
        ],
    )

    assert response.status_code == 200
    results = {r["filename"]: r for r in response.json()["results"]}
    assert results["BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip"]["error"] is None
    assert results["corrupt.zip"]["error"] is not None


def test_upload_unrecognized_filename_reports_error(client, db_session):
    _login_admin(client, db_session)

    zip_data = _zip_bytes("data.csv", CURRENT_CSV)
    response = client.post(
        "/api/admin/market-data/upload",
        files={"files": ("my_download.zip", zip_data, "application/zip")},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["error"] is not None
    assert result["trade_date"] is None


def test_sync_history_reflects_uploads(client, db_session):
    _login_admin(client, db_session)
    _seed_company(db_session, "TCS", "Tata Consultancy Services Ltd")

    zip_data = _zip_bytes("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv", CURRENT_CSV)
    client.post(
        "/api/admin/market-data/upload",
        files={"files": ("BhavCopy_NSE_CM_0_0_0_20251222_F_0000.csv.zip", zip_data, "application/zip")},
    )

    response = client.get("/api/admin/market-data/sync-history")
    assert response.status_code == 200
    body = response.json()
    assert body["last_sync"] is not None
    assert body["last_sync"]["source"] == "manual_upload"
    assert len(body["history"]) >= 1
