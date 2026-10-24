def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["market_data_provider"] == "mock"
    assert body["ai_provider"] == "mock"
    assert body["last_sync_check_at"] is None


def test_health_check_reports_last_sync_check_even_when_zero_rows_synced(client, db_session):
    from datetime import date

    from app.models.sync_log import MarketDataSyncLog, SyncSource, SyncStatus

    db_session.add(
        MarketDataSyncLog(
            trade_date=date(2026, 10, 2),
            source=SyncSource.scheduled,
            status=SyncStatus.success,
            rows_synced=0,  # a holiday - no new data, but the check still happened
        )
    )
    db_session.commit()

    response = client.get("/api/health")
    body = response.json()
    assert body["last_sync_check_at"] is not None
