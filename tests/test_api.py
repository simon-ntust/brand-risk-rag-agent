from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import LLMJudgment, PolicyMatch


def test_health_check():
    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        TestClient(app) as client,
    ):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_triage_valid_payload():
    mock_state = {
        "retrieved_policies": [
            PolicyMatch(
                policy_id="APEX-03",
                title="Unverified Brand Mention / Fan Commentary",
                rule_text="Personal accounts mentioning ApexBank casually are LOW risk.",
                similarity=0.82,
            )
        ],
        "judgment": LLMJudgment(
            risk_level="LOW",
            confidence=0.94,
            cited_policy_id="APEX-03",
            reasoning="Profile belongs to a casual runner with no impersonation signals.",
        ),
        "requires_human_review": False,
    }

    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.triage_graph.ainvoke", new_callable=AsyncMock, return_value=mock_state),
        TestClient(app) as client,
    ):
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
        assert data["cited_policy_id"] == "APEX-03"
        assert data["requires_human_review"] is False


def test_triage_rejects_missing_fields():
    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        TestClient(app) as client,
    ):
        response = client.post(
            "/api/v1/triage",
            json={"brand": "ApexBank"},
        )
        assert response.status_code == 422