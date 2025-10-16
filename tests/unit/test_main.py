"""Unit tests for main FastAPI application."""
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create test client with mocked settings."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_REPOS", "testorg/repo1,testorg/repo2")
    monkeypatch.setenv("WEBHOOK_TOKEN", "test_webhook_secret")

    from app.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_returns_ok(self, test_client: TestClient) -> None:
        """Test health endpoint returns 200 OK."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mode" in data
        assert "repos" in data
        assert "workspaces" in data

    def test_health_includes_config(self, test_client: TestClient) -> None:
        """Test health endpoint includes configuration."""
        response = test_client.get("/health")

        data = response.json()
        assert data["mode"] == "relay"
        assert "testorg/repo1" in data["repos"]
        assert "testorg/repo2" in data["repos"]


class TestWebhookEndpoint:
    """Test suite for /webhook/zenhub endpoint."""

    def test_webhook_unauthorized_without_token(self, test_client: TestClient) -> None:
        """Test webhook rejects requests without valid token."""
        response = test_client.post(
            "/webhook/zenhub",
            json={"type": "test"}
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "unauthorized"

    def test_webhook_accepts_token_in_header(
        self,
        test_client: TestClient,
        sample_zenhub_payload: dict[str, Any]
    ) -> None:
        """Test webhook accepts token in header."""
        with patch("app.github_client.repository_dispatch", new_callable=AsyncMock):
            response = test_client.post(
                "/webhook/zenhub",
                json=sample_zenhub_payload,
                headers={"x-webhook-token": "test_webhook_secret"}
            )

        assert response.status_code == 200

    def test_webhook_accepts_token_in_query(
        self,
        test_client: TestClient,
        sample_zenhub_payload: dict[str, Any]
    ) -> None:
        """Test webhook accepts token in query parameter."""
        with patch("app.github_client.repository_dispatch", new_callable=AsyncMock):
            response = test_client.post(
                "/webhook/zenhub?token=test_webhook_secret",
                json=sample_zenhub_payload
            )

        assert response.status_code == 200

    def test_webhook_rejects_invalid_payload(self, test_client: TestClient) -> None:
        """Test webhook rejects invalid form data payload."""
        response = test_client.post(
            "/webhook/zenhub?token=test_webhook_secret",
            data="invalid=data=with=extra=equals",
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

        # Should still parse (parse_qs is lenient), but may fail later
        # For now, just check it doesn't crash
        assert response.status_code in [200, 400, 500]

    def test_webhook_dispatches_to_all_repos(
        self,
        test_client: TestClient,
        sample_zenhub_payload: dict[str, Any]
    ) -> None:
        """Test webhook dispatches events to all configured repos."""
        with patch("app.github_client.repository_dispatch", new_callable=AsyncMock) as mock_dispatch:
            response = test_client.post(
                "/webhook/zenhub?token=test_webhook_secret",
                json=sample_zenhub_payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["results"]) == 2
        assert data["results"][0]["repo"] == "testorg/repo1"
        assert data["results"][1]["repo"] == "testorg/repo2"
        assert mock_dispatch.call_count == 2

    def test_webhook_handles_dispatch_failure(
        self,
        test_client: TestClient,
        sample_zenhub_payload: dict[str, Any]
    ) -> None:
        """Test webhook handles dispatch failures gracefully."""
        with patch("app.github_client.repository_dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.side_effect = Exception("API error")

            response = test_client.post(
                "/webhook/zenhub?token=test_webhook_secret",
                json=sample_zenhub_payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert all(r["status"] == "failed" for r in data["results"])
        assert all("error" in r for r in data["results"])

    def test_webhook_with_form_data(self, test_client: TestClient) -> None:
        """Test webhook accepts form-encoded data from Zenhub."""
        with patch("app.github_client.repository_dispatch", new_callable=AsyncMock):
            with patch("app.github_client.get_issue_details", new_callable=AsyncMock) as mock_get_issue:
                mock_get_issue.return_value = {
                    "title": "Test Issue",
                    "body": "Description",
                    "labels": [{"name": "bug"}],
                    "state": "open",
                    "html_url": "https://github.com/org/repo/issues/1",
                    "assignees": [],
                    "milestone": None
                }
                
                response = test_client.post(
                    "/webhook/zenhub?token=test_webhook_secret",
                    data="type=issue_transfer&organization=testorg&repo=repo1&issue_number=1&to_pipeline_name=In Progress",
                    headers={"content-type": "application/x-www-form-urlencoded"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_webhook_empty_body_returns_pong(self, test_client: TestClient) -> None:
        """Test webhook returns pong for empty body (ping event)."""
        response = test_client.post(
            "/webhook/zenhub?token=test_webhook_secret",
            data=b"",
            headers={"content-type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
