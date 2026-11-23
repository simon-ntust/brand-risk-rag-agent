from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_triage_valid_payload():
    response = client.post(
        "/api/v1/triage",
        json={
            "brand": "ApexBank",
            "handle": "@daily_runner",
            "display_name": "Alex Lin",
            "bio": "Weekend runner in Taipei.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["brand"] == "ApexBank"
    assert data["risk_level"] == "LOW"
    assert data["requires_human_review"] is False


def test_triage_rejects_missing_fields():
    response = client.post(
        "/api/v1/triage",
        json={"brand": "ApexBank"},
    )
    assert response.status_code == 422