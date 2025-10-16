"""Unit tests for PR service."""

from unittest.mock import AsyncMock

import pytest

from app.services.pr_service import PRService


class TestPRService:
    """Tests for PRService."""

    @pytest.fixture
    def mock_github_client(self) -> AsyncMock:
        """Create mock GitHub client."""
        client = AsyncMock()
        client.create_branch = AsyncMock()
        client.create_file = AsyncMock(
            return_value={"content": {"sha": "abc123"}, "commit": {"sha": "def456"}}
        )
        client.create_pull_request = AsyncMock(
            return_value={"number": 42, "html_url": "https://github.com/org/repo/pull/42"}
        )
        return client

    @pytest.fixture
    def pr_service(self, mock_github_client: AsyncMock) -> PRService:
        """Create PRService with mock client."""
        return PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

    @pytest.mark.asyncio
    async def test_creates_pr_for_in_progress_with_assignees(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that PR is created when issue moves to In Progress with assignees."""
        payload = {
            "type": "issue.transfer",
            "to_pipeline_name": "In Progress",
            "issue_number": "123",
            "organization": "testorg",
            "repo": "testrepo",
            "github_issue": {
                "title": "Add new feature",
                "body": "This is a test issue",
                "labels": [{"name": "bug"}, {"name": "enhancement"}],
                "assignees": [{"login": "user1"}],
                "html_url": "https://github.com/testorg/testrepo/issues/123",
                "milestone": {"title": "v1.0"},
            },
            "zenhub_issue": {"estimate": {"value": 5}},
        }

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is not None
        assert result["branch"] == "feature/123-add-new-feature"
        assert result["pr_number"] == 42
        assert result["pr_url"] == "https://github.com/org/repo/pull/42"

        # Verify branch was created
        mock_github_client.create_branch.assert_called_once_with(
            "testorg", "testrepo", "feature/123-add-new-feature", "develop", "test_token"
        )

        # Verify PR was created
        call_args = mock_github_client.create_pull_request.call_args
        assert call_args[1]["owner"] == "testorg"
        assert call_args[1]["repo"] == "testrepo"
        assert call_args[1]["title"] == "[WIP] Add new feature"
        assert call_args[1]["head"] == "feature/123-add-new-feature"
        assert call_args[1]["base"] == "develop"
        assert call_args[1]["draft"] is True
        assert "Closes #123" in call_args[1]["body"]
        assert "This is a test issue" in call_args[1]["body"]

    @pytest.mark.asyncio
    async def test_skips_pr_for_wrong_event_type(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that PR is not created for non-transfer events."""
        payload = {
            "type": "issue.comment",
            "to_pipeline_name": "In Progress",
            "issue_number": "123",
            "github_issue": {"assignees": [{"login": "user1"}]},
        }

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is None
        mock_github_client.create_branch.assert_not_called()
        mock_github_client.create_pull_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_pr_for_wrong_pipeline(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that PR is not created when not moving to In Progress."""
        payload = {
            "type": "issue.transfer",
            "to_pipeline_name": "Done",
            "issue_number": "123",
            "github_issue": {"assignees": [{"login": "user1"}]},
        }

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is None
        mock_github_client.create_branch.assert_not_called()
        mock_github_client.create_pull_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_pr_without_assignees(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that PR is not created if issue has no assignees."""
        payload = {
            "type": "issue.transfer",
            "to_pipeline_name": "In Progress",
            "issue_number": "123",
            "github_issue": {"title": "Test", "assignees": []},
        }

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is None
        mock_github_client.create_branch.assert_not_called()
        mock_github_client.create_pull_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_api_errors_gracefully(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that API errors are handled gracefully."""
        payload = {
            "type": "issue.transfer",
            "to_pipeline_name": "In Progress",
            "issue_number": "123",
            "github_issue": {
                "title": "Test",
                "assignees": [{"login": "user1"}],
                "html_url": "https://github.com/testorg/testrepo/issues/123",
            },
        }

        # Make create_branch fail
        mock_github_client.create_branch.side_effect = Exception("API error")

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is None
        mock_github_client.create_pull_request.assert_not_called()

    def test_generate_branch_name_sanitizes_title(self, pr_service: PRService) -> None:
        """Test that branch names are properly sanitized."""
        # Test with special characters
        branch = pr_service._generate_branch_name(123, "Fix: Add @special & chars!")
        assert branch == "feature/123-fix-add-special-chars"

        # Test with very long title
        long_title = "A" * 100
        branch = pr_service._generate_branch_name(456, long_title)
        assert len(branch) <= len("feature/456-") + 50
        assert branch.startswith("feature/456-")

    def test_generate_pr_body_includes_issue_context(self, pr_service: PRService) -> None:
        """Test that PR body includes relevant issue context."""
        payload = {
            "issue_number": "123",
            "github_issue": {
                "html_url": "https://github.com/org/repo/issues/123",
                "body": "Issue description here",
                "labels": [{"name": "bug"}, {"name": "priority"}],
                "assignees": [{"login": "user1"}, {"login": "user2"}],
                "milestone": {"title": "v2.0"},
            },
            "zenhub_issue": {"estimate": {"value": 8}},
        }

        body = pr_service._generate_pr_body(payload)

        assert "Closes #123" in body
        assert "Issue description here" in body
        assert "`bug`" in body
        assert "`priority`" in body
        assert "@user1" in body
        assert "@user2" in body
        assert "v2.0" in body
        assert "8 points" in body

    def test_generate_context_file_includes_all_metadata(self, pr_service: PRService) -> None:
        """Test that context file includes all GitHub and Zenhub metadata."""
        payload = {
            "type": "issue_transfer",
            "organization": "testorg",
            "repo": "testrepo",
            "workspace_name": "Test Workspace",
            "from_pipeline_name": "Backlog",
            "to_pipeline_name": "In Progress",
            "github_issue": {
                "html_url": "https://github.com/testorg/testrepo/issues/456",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "title": "Test Issue",
                "body": "Full issue description here",
                "labels": [{"name": "bug"}, {"name": "enhancement"}],
                "assignees": [{"login": "developer1"}, {"login": "developer2"}],
                "milestone": {"title": "v3.0"},
            },
            "zenhub_issue": {
                "estimate": {"value": 13},
                "pipeline": {"name": "In Progress"},
                "epic": {"issue_number": 100},
            },
        }

        content = pr_service._generate_context_file(payload, 456)

        # Check header
        assert "# Issue #456: Test Issue" in content
        assert "Moved to In Progress:" in content

        # Check GitHub metadata
        assert "## GitHub Metadata" in content
        assert "https://github.com/testorg/testrepo/issues/456" in content
        assert "**State:** open" in content
        assert "**Created:** 2025-01-01T00:00:00Z" in content

        # Check labels, assignees, milestone
        assert "`bug`" in content
        assert "`enhancement`" in content
        assert "@developer1" in content
        assert "@developer2" in content
        assert "**Milestone:** v3.0" in content

        # Check Zenhub metadata
        assert "## Zenhub Metadata" in content
        assert "**Estimate:** 13 points" in content
        assert "**Pipeline:** In Progress" in content
        assert "**Epic:** #100" in content

        # Check issue description
        assert "## Issue Description" in content
        assert "Full issue description here" in content

        # Check automation metadata
        assert "## Automation Metadata" in content
        assert "**Workflow:** issue_transfer" in content
        assert "**Repository:** testorg/testrepo" in content
        assert "**Workspace:** Test Workspace" in content
        assert "**From Pipeline:** Backlog" in content
        assert "**To Pipeline:** In Progress" in content
        assert "auto-generated by zenhub-bot" in content

    @pytest.mark.asyncio
    async def test_creates_pr_with_context_file(
        self, pr_service: PRService, mock_github_client: AsyncMock
    ) -> None:
        """Test that context file is created before PR."""
        payload = {
            "type": "issue.transfer",
            "to_pipeline_name": "In Progress",
            "issue_number": "789",
            "organization": "testorg",
            "repo": "testrepo",
            "github_issue": {
                "title": "Context Test",
                "body": "Testing context file",
                "assignees": [{"login": "user1"}],
                "html_url": "https://github.com/testorg/testrepo/issues/789",
            },
        }

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        assert result is not None

        # Verify context file was created
        mock_github_client.create_file.assert_called_once()
        file_call = mock_github_client.create_file.call_args
        assert file_call[1]["owner"] == "testorg"
        assert file_call[1]["repo"] == "testrepo"
        assert file_call[1]["path"] == ".github/ISSUE_789.md"
        assert file_call[1]["branch"] == "feature/789-context-test"
        assert file_call[1]["message"] == "chore: add issue context for #789"
        assert "# Issue #789: Context Test" in file_call[1]["content"]
        assert "Testing context file" in file_call[1]["content"]
