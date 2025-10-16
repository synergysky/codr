"""Integration tests for webhook flow with realistic Zenhub payloads."""

from unittest.mock import AsyncMock

import pytest

from tests.fixtures import zenhub_webhooks


@pytest.mark.integration
class TestWebhookToPRFlow:
    """Test the complete flow from webhook to PR creation."""

    @pytest.fixture
    def mock_github_client(self) -> AsyncMock:
        """Mock GitHub client with realistic responses."""
        client = AsyncMock()
        client.get_issue_details = AsyncMock(
            return_value=zenhub_webhooks.github_issue_with_assignees()
        )
        client.get_repository_id = AsyncMock(return_value=123456)
        client.create_branch = AsyncMock(
            return_value={"ref": "refs/heads/feature/123-add-new-feature"}
        )
        client.create_file = AsyncMock(
            return_value={"content": {"sha": "abc123"}, "commit": {"sha": "def456"}}
        )
        client.create_pull_request = AsyncMock(
            return_value={
                "number": 42,
                "html_url": "https://github.com/testorg/testrepo/pull/42",
                "title": "[WIP] Add new feature for user authentication",
            }
        )
        return client

    @pytest.fixture
    def mock_zenhub_client(self) -> AsyncMock:
        """Mock Zenhub client with realistic responses."""
        client = AsyncMock()
        client.get_issue_data = AsyncMock(return_value=zenhub_webhooks.zenhub_issue_data())
        return client

    @pytest.mark.asyncio
    async def test_issue_moved_to_in_progress_creates_pr(
        self, mock_github_client: AsyncMock, mock_zenhub_client: AsyncMock
    ) -> None:
        """Test that moving issue to In Progress creates PR (with or without assignees)."""
        from app.services.enrichers import GitHubEnricher, ZenhubEnricher
        from app.services.pr_service import PRService
        from app.services.webhook_service import WebhookService

        # Setup enrichers
        github_enricher = GitHubEnricher(
            github_client=mock_github_client, github_token="test_token"
        )
        zenhub_enricher = ZenhubEnricher(
            zenhub_client=mock_zenhub_client,
            github_client=mock_github_client,
            github_token="test_token",
            zenhub_token="test_zenhub_token",
        )
        webhook_service = WebhookService(enrichers=[github_enricher, zenhub_enricher])

        # Setup PR service
        pr_service = PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

        # Simulate webhook payload
        raw_payload = zenhub_webhooks.issue_transfer_to_in_progress()

        # Enrich payload
        enriched = await webhook_service.process_webhook(raw_payload)

        # Attempt PR creation
        result = await pr_service.handle_issue_moved(
            enriched, raw_payload["organization"], raw_payload["repo"]
        )

        # Verify PR was created
        assert result is not None
        assert result["branch"] == "feature/123-add-new-feature-for-user-authentication"
        assert result["pr_number"] == 42
        assert "github.com" in result["pr_url"]

        # Verify GitHub API calls
        mock_github_client.create_branch.assert_called_once()
        mock_github_client.create_file.assert_called_once()  # Context file created
        mock_github_client.create_pull_request.assert_called_once()

        # Verify PR details
        pr_call = mock_github_client.create_pull_request.call_args
        assert pr_call[1]["draft"] is True
        assert pr_call[1]["base"] == "develop"
        assert "Closes #123" in pr_call[1]["body"]
        assert "OAuth2 authentication" in pr_call[1]["body"]

    @pytest.mark.asyncio
    async def test_issue_without_assignees_creates_pr(
        self, mock_github_client: AsyncMock, mock_zenhub_client: AsyncMock
    ) -> None:
        """Test that issues without assignees still create PRs."""
        from app.services.pr_service import PRService

        # Mock GitHub to return issue without assignees
        mock_github_client.get_issue_details = AsyncMock(
            return_value=zenhub_webhooks.github_issue_without_assignees()
        )

        pr_service = PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

        # Use enriched payload without assignees
        payload = zenhub_webhooks.enriched_payload_no_assignees()

        result = await pr_service.handle_issue_moved(payload, "testorg", "testrepo")

        # PR should be created even without assignees
        assert result is not None
        mock_github_client.create_branch.assert_called_once()
        mock_github_client.create_file.assert_called_once()
        mock_github_client.create_pull_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_moved_to_done_skips_pr(
        self, mock_github_client: AsyncMock, mock_zenhub_client: AsyncMock
    ) -> None:
        """Test that moving to Done pipeline doesn't create PR."""
        from app.services.enrichers import GitHubEnricher
        from app.services.pr_service import PRService
        from app.services.webhook_service import WebhookService

        github_enricher = GitHubEnricher(
            github_client=mock_github_client, github_token="test_token"
        )
        webhook_service = WebhookService(enrichers=[github_enricher])

        pr_service = PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

        # Webhook for moving to Done
        raw_payload = zenhub_webhooks.issue_transfer_to_done()
        enriched = await webhook_service.process_webhook(raw_payload)

        result = await pr_service.handle_issue_moved(enriched, "testorg", "testrepo")

        assert result is None
        mock_github_client.create_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_pr_body_includes_all_context(
        self, mock_github_client: AsyncMock, mock_zenhub_client: AsyncMock
    ) -> None:
        """Test that PR body includes all relevant issue context."""
        from app.services.enrichers import GitHubEnricher, ZenhubEnricher
        from app.services.pr_service import PRService
        from app.services.webhook_service import WebhookService

        github_enricher = GitHubEnricher(
            github_client=mock_github_client, github_token="test_token"
        )
        zenhub_enricher = ZenhubEnricher(
            zenhub_client=mock_zenhub_client,
            github_client=mock_github_client,
            github_token="test_token",
            zenhub_token="test_token",
        )
        webhook_service = WebhookService(enrichers=[github_enricher, zenhub_enricher])

        pr_service = PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

        raw_payload = zenhub_webhooks.issue_transfer_to_in_progress()
        enriched = await webhook_service.process_webhook(raw_payload)

        result = await pr_service.handle_issue_moved(enriched, "testorg", "testrepo")

        # Verify PR was created
        assert result is not None
        mock_github_client.create_file.assert_called_once()

        pr_call = mock_github_client.create_pull_request.call_args
        body = pr_call[1]["body"]

        # Verify all expected content
        assert "Closes #123" in body
        assert "OAuth2 authentication" in body  # Issue description
        assert "`enhancement`" in body  # Labels
        assert "`priority:high`" in body
        assert "@developer1" in body  # Assignees
        assert "@developer2" in body
        assert "v2.0" in body  # Milestone
        assert "8 points" in body  # Zenhub estimate

    @pytest.mark.asyncio
    async def test_branch_name_sanitization(self, mock_github_client: AsyncMock) -> None:
        """Test that branch names are properly sanitized."""
        from app.services.pr_service import PRService

        pr_service = PRService(
            github_client=mock_github_client, github_token="test_token", base_branch="develop"
        )

        # Test various problematic titles
        test_cases = [
            ("Fix: Bug in payment!", "feature/123-fix-bug-in-payment"),
            ("Add @mentions & special chars", "feature/456-add-mentions-special-chars"),
            ("Support UTF-8 émojis 🎉", "feature/789-support-utf-8-mojis"),
        ]

        for title, expected_branch in test_cases:
            issue_num = int(expected_branch.split("/")[1].split("-")[0])
            branch = pr_service._generate_branch_name(issue_num, title)
            assert branch == expected_branch
