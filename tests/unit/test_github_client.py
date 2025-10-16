"""Unit tests for GitHub client module."""
from unittest.mock import AsyncMock, patch

import pytest

from app.github_client import repository_dispatch


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
