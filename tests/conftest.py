"""Shared test fixtures and configuration."""
import pytest
from typing import Any


@pytest.fixture
def mock_settings() -> dict[str, Any]:
    """Mock settings for testing."""
    return {
        "GITHUB_TOKEN": "test_token_123",
        "GITHUB_REPOS": "testorg/repo1,testorg/repo2",
        "WEBHOOK_TOKEN": "test_webhook_secret",
        "ZENHUB_PIPELINE_NAME": "In Progress",
        "MODE": "relay",
        "DISPATCH_EVENT": "zenhub_in_progress",
        "BASE_BRANCH_DEFAULT": "develop",
        "BASE_BRANCH_HOTFIX": "hotfix_branch",
        "HOTFIX_LABEL": "hotfix",
    }


@pytest.fixture
def sample_zenhub_payload() -> dict[str, Any]:
    """Sample Zenhub webhook payload."""
    return {
        "type": "issue.transfer",
        "issue_number": 123,
        "repo_id": 456789,
        "workspace_id": "workspace123",
        "from_pipeline": {"name": "Backlog"},
        "to_pipeline": {"name": "In Progress"},
        "user": {"username": "developer1"},
    }
