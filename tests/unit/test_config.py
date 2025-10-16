"""Unit tests for configuration module."""
import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_with_valid_repos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings initialization with valid repo configuration."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "org1/repo1,org2/repo2")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")

        settings = Settings()

        assert settings.GITHUB_TOKEN == "test_token"
        assert settings.WEBHOOK_TOKEN == "secret"
        assert settings.get_repos() == ["org1/repo1", "org2/repo2"]

    def test_settings_invalid_repo_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings validation fails with invalid repo format."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "invalid-repo-format")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "Invalid repo format" in str(exc_info.value)

    def test_settings_empty_repos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings validation fails with empty repos."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "must contain at least one repo" in str(exc_info.value)

    def test_get_workspace_ids_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_workspace_ids returns empty list when not configured."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "org/repo")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")
        monkeypatch.setenv("ZENHUB_WORKSPACE_IDS", "")

        settings = Settings()

        assert settings.get_workspace_ids() == []

    def test_get_workspace_ids_multiple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get_workspace_ids parses comma-separated values."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "org/repo")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")
        monkeypatch.setenv("ZENHUB_WORKSPACE_IDS", "ws1,ws2,ws3")

        settings = Settings()

        assert settings.get_workspace_ids() == ["ws1", "ws2", "ws3"]

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test default configuration values."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPOS", "org/repo")
        monkeypatch.setenv("WEBHOOK_TOKEN", "secret")

        settings = Settings()

        assert settings.MODE == "relay"
        assert settings.DISPATCH_EVENT == "zenhub_in_progress"
        assert settings.BASE_BRANCH_DEFAULT == "develop"
        assert settings.BASE_BRANCH_HOTFIX == "hotfix_branch"
        assert settings.HOTFIX_LABEL == "hotfix"
        assert settings.ZENHUB_PIPELINE_NAME == "In Progress"
        assert settings.PORT == 8000
