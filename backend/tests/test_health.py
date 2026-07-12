"""Phase 0 smoke test — verifies the backend starts and health endpoint works."""


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "qshield-backend"
    assert "timestamp" in data
    assert "version" in data
