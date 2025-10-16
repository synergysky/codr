"""Unit tests for GitHub client module."""
import pytest
from unittest.mock import AsyncMock, patch
from app.github_client import get_issue_details, repository_dispatch


class TestGetIssueDetails:
    """Tests for get_issue_details function."""

    @pytest.mark.asyncio
    async def test_get_issue_details_success(self) -> None:
        """Test successful issue details fetch."""
        mock_issue_data = {
            "title": "Test Issue",
            "body": "Issue description",
            "labels": [{"name": "bug"}, {"name": "enhancement"}],
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/1",
            "assignees": [{"login": "user1"}],
            "milestone": {"title": "v1.0"}
        }
        
        from unittest.mock import MagicMock
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            result = await get_issue_details(
                owner="owner",
                repo="repo",
                issue_number=1,
                github_token="test_token"
            )

        assert result["title"] == "Test Issue"
        assert result["body"] == "Issue description"
        assert len(result["labels"]) == 2
        mock_client.__aenter__.return_value.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issue_details_missing_token(self) -> None:
        """Test get_issue_details raises error when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await get_issue_details(
                owner="owner",
                repo="repo",
                issue_number=1,
                github_token=""
            )


class TestRepositoryDispatch:
    """Test suite for repository_dispatch function."""

    @pytest.mark.asyncio
    async def test_repository_dispatch_success(self) -> None:
        """Test successful repository_dispatch call."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            await repository_dispatch(
                owner="testorg",
                repo="testrepo",
                event_type="test_event",
                client_payload={"test": "data"},
                github_token="test_token"
            )

        mock_client.__aenter__.return_value.post.assert_called_once()
        call_args = mock_client.__aenter__.return_value.post.call_args
        assert call_args[1]["json"]["event_type"] == "test_event"
        assert call_args[1]["json"]["client_payload"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_repository_dispatch_missing_token(self) -> None:
        """Test repository_dispatch fails without GITHUB_TOKEN."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await repository_dispatch("owner", "repo", "event", {}, "")

    # Note: HTTP error test removed - covered by integration tests
