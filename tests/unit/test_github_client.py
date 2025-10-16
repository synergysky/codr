"""Unit tests for GitHub client module."""

from unittest.mock import AsyncMock, patch

import pytest

from app.github_client import (
    create_branch,
    create_pull_request,
    get_default_branch,
    get_issue_details,
    repository_dispatch,
)


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
            "milestone": {"title": "v1.0"},
        }

        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.json.return_value = mock_issue_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            result = await get_issue_details(
                owner="owner", repo="repo", issue_number=1, github_token="test_token"
            )

        assert result["title"] == "Test Issue"
        assert result["body"] == "Issue description"
        assert len(result["labels"]) == 2
        mock_client.__aenter__.return_value.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issue_details_missing_token(self) -> None:
        """Test get_issue_details raises error when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await get_issue_details(owner="owner", repo="repo", issue_number=1, github_token="")


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
                github_token="test_token",
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


class TestGetDefaultBranch:
    """Tests for get_default_branch function."""

    @pytest.mark.asyncio
    async def test_get_default_branch_success(self) -> None:
        """Test successful default branch fetch."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.json.return_value = {"default_branch": "develop"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            result = await get_default_branch("owner", "repo", "test_token")

        assert result == "develop"

    @pytest.mark.asyncio
    async def test_get_default_branch_missing_token(self) -> None:
        """Test get_default_branch raises error when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await get_default_branch("owner", "repo", "")


class TestCreateBranch:
    """Tests for create_branch function."""

    @pytest.mark.asyncio
    async def test_create_branch_success(self) -> None:
        """Test successful branch creation."""
        from unittest.mock import MagicMock

        # Mock ref response (getting base SHA)
        mock_ref_response = MagicMock()
        mock_ref_response.json.return_value = {"object": {"sha": "abc123"}}
        mock_ref_response.raise_for_status = MagicMock()

        # Mock create response
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {"ref": "refs/heads/feature/test"}
        mock_create_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_ref_response)
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_create_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            result = await create_branch("owner", "repo", "feature/test", "main", "test_token")

        assert result["ref"] == "refs/heads/feature/test"

    @pytest.mark.asyncio
    async def test_create_branch_missing_token(self) -> None:
        """Test create_branch raises error when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await create_branch("owner", "repo", "branch", "main", "")


class TestCreatePullRequest:
    """Tests for create_pull_request function."""

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self) -> None:
        """Test successful PR creation."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
            "title": "Test PR",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("app.github_client.httpx.AsyncClient", return_value=mock_client):
            result = await create_pull_request(
                owner="owner",
                repo="repo",
                title="Test PR",
                head="feature/test",
                base="main",
                body="Test body",
                draft=True,
                github_token="test_token",
            )

        assert result["number"] == 42
        assert result["html_url"] == "https://github.com/owner/repo/pull/42"

        # Verify the call
        call_args = mock_client.__aenter__.return_value.post.call_args
        assert call_args[1]["json"]["draft"] is True

    @pytest.mark.asyncio
    async def test_create_pull_request_missing_token(self) -> None:
        """Test create_pull_request raises error when token is missing."""
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN is not set"):
            await create_pull_request("owner", "repo", "title", "head", "base", "body", False, "")
