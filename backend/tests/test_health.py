def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["market_data_provider"] == "mock"
    assert body["ai_provider"] == "mock"
