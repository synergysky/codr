"""Unit tests for service layer."""
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from app.services.webhook_service import WebhookService
from app.services.enrichers import GitHubEnricher, ZenhubEnricher


class TestWebhookService:
    """Tests for WebhookService."""

    @pytest.fixture
    def mock_enrichers(self) -> list[AsyncMock]:
        """Create mock enrichers."""
        github_enricher = AsyncMock()
        github_enricher.enrich.return_value = {
            'github_issue': {
                'title': 'Test Issue',
                'labels': ['bug']
            }
        }
        
        zenhub_enricher = AsyncMock()
        zenhub_enricher.enrich.return_value = {
            'zenhub_issue': {
                'estimate': 3,
                'pipeline': 'In Progress'
            }
        }
        
        return [github_enricher, zenhub_enricher]

    @pytest.fixture
    def webhook_service(self, mock_enrichers: list[AsyncMock]) -> WebhookService:
        """Create WebhookService with mock enrichers."""
        return WebhookService(enrichers=mock_enrichers)

    @pytest.mark.asyncio
    async def test_process_webhook_enriches_payload(
        self,
        webhook_service: WebhookService,
        mock_enrichers: list[AsyncMock]
    ) -> None:
        """Test that webhook service enriches payload with all enrichers."""
        payload = {
            'type': 'issue_transfer',
            'organization': 'testorg',
            'repo': 'testrepo',
            'issue_number': '123'
        }

        result = await webhook_service.process_webhook(payload)

        # Verify all enrichers were called (with progressively enriched payload)
        assert mock_enrichers[0].enrich.call_count == 1
        assert mock_enrichers[1].enrich.call_count == 1

        # Verify payload was enriched
        assert 'github_issue' in result
        assert 'zenhub_issue' in result
        assert result['github_issue']['title'] == 'Test Issue'
        assert result['zenhub_issue']['estimate'] == 3

    @pytest.mark.asyncio
    async def test_process_webhook_handles_enricher_failure(
        self,
        webhook_service: WebhookService,
        mock_enrichers: list[AsyncMock]
    ) -> None:
        """Test that webhook service continues if one enricher fails."""
        payload = {'type': 'issue_transfer'}
        
        # Make first enricher fail
        mock_enrichers[0].enrich.side_effect = Exception("API error")

        result = await webhook_service.process_webhook(payload)

        # Should still have data from second enricher
        assert 'zenhub_issue' in result
        assert result['zenhub_issue']['estimate'] == 3

    @pytest.mark.asyncio
    async def test_process_webhook_returns_original_on_all_failures(
        self,
        webhook_service: WebhookService,
        mock_enrichers: list[AsyncMock]
    ) -> None:
        """Test that webhook service returns original payload if all enrichers fail."""
        payload = {'type': 'issue_transfer', 'issue_number': '123'}
        
        # Make all enrichers fail
        for enricher in mock_enrichers:
            enricher.enrich.side_effect = Exception("API error")

        result = await webhook_service.process_webhook(payload)

        # Should return original payload
        assert result['type'] == 'issue_transfer'
        assert result['issue_number'] == '123'


class TestGitHubEnricher:
    """Tests for GitHubEnricher."""

    @pytest.fixture
    def mock_github_client(self) -> AsyncMock:
        """Create mock GitHub client."""
        client = AsyncMock()
        client.get_issue_details.return_value = {
            'title': 'Test Issue',
            'body': 'Issue description',
            'labels': [{'name': 'bug'}, {'name': 'enhancement'}],
            'state': 'open',
            'html_url': 'https://github.com/org/repo/issues/1',
            'assignees': [{'login': 'user1'}],
            'milestone': {'title': 'v1.0'}
        }
        return client

    @pytest.fixture
    def github_enricher(self, mock_github_client: AsyncMock) -> GitHubEnricher:
        """Create GitHubEnricher with mock client."""
        return GitHubEnricher(github_client=mock_github_client)

    @pytest.mark.asyncio
    async def test_enrich_adds_github_issue_data(
        self,
        github_enricher: GitHubEnricher,
        mock_github_client: AsyncMock
    ) -> None:
        """Test that GitHubEnricher adds issue data to payload."""
        payload = {
            'organization': 'testorg',
            'repo': 'testrepo',
            'issue_number': '123'
        }

        result = await github_enricher.enrich(payload)

        # Verify GitHub API was called
        mock_github_client.get_issue_details.assert_called_once_with(
            'testorg', 'testrepo', 123
        )

        # Verify enriched data
        assert 'github_issue' in result
        assert result['github_issue']['title'] == 'Test Issue'
        assert result['github_issue']['labels'] == ['bug', 'enhancement']
        assert len(result['github_issue']['assignees']) == 1

    @pytest.mark.asyncio
    async def test_enrich_skips_if_missing_data(
        self,
        github_enricher: GitHubEnricher
    ) -> None:
        """Test that GitHubEnricher skips if required data is missing."""
        payload = {'type': 'issue_transfer'}  # Missing org/repo/issue_number

        result = await github_enricher.enrich(payload)

        # Should return original payload unchanged
        assert result == payload
        assert 'github_issue' not in result

    @pytest.mark.asyncio
    async def test_enrich_handles_api_error(
        self,
        github_enricher: GitHubEnricher,
        mock_github_client: AsyncMock
    ) -> None:
        """Test that GitHubEnricher handles API errors gracefully."""
        payload = {
            'organization': 'testorg',
            'repo': 'testrepo',
            'issue_number': '123'
        }
        mock_github_client.get_issue_details.side_effect = Exception("API error")

        result = await github_enricher.enrich(payload)

        # Should return original payload
        assert result == payload
        assert 'github_issue' not in result


class TestZenhubEnricher:
    """Tests for ZenhubEnricher."""

    @pytest.fixture
    def mock_zenhub_client(self) -> AsyncMock:
        """Create mock Zenhub client."""
        client = AsyncMock()
        client.get_issue_data.return_value = {
            'estimate': {'value': 5},
            'pipeline': {'name': 'In Progress'},
            'is_epic': False,
            'epic': None
        }
        return client

    @pytest.fixture
    def mock_github_client(self) -> AsyncMock:
        """Create mock GitHub client for repo ID."""
        client = AsyncMock()
        client.get_repository_id.return_value = 12345
        return client

    @pytest.fixture
    def zenhub_enricher(
        self,
        mock_zenhub_client: AsyncMock,
        mock_github_client: AsyncMock
    ) -> ZenhubEnricher:
        """Create ZenhubEnricher with mock clients."""
        return ZenhubEnricher(
            zenhub_client=mock_zenhub_client,
            github_client=mock_github_client,
            zenhub_token="test_token"
        )

    @pytest.mark.asyncio
    async def test_enrich_adds_zenhub_issue_data(
        self,
        zenhub_enricher: ZenhubEnricher,
        mock_zenhub_client: AsyncMock,
        mock_github_client: AsyncMock
    ) -> None:
        """Test that ZenhubEnricher adds issue data to payload."""
        payload = {
            'organization': 'testorg',
            'repo': 'testrepo',
            'issue_number': '123',
            'workspace_id': 'ws123'
        }

        result = await zenhub_enricher.enrich(payload)

        # Verify GitHub repo ID was fetched
        mock_github_client.get_repository_id.assert_called_once_with('testorg', 'testrepo')

        # Verify Zenhub API was called
        mock_zenhub_client.get_issue_data.assert_called_once_with(
            'ws123', 12345, 123
        )

        # Verify enriched data
        assert 'zenhub_issue' in result
        assert result['zenhub_issue']['estimate'] == 5
        assert result['zenhub_issue']['pipeline'] == 'In Progress'

    @pytest.mark.asyncio
    async def test_enrich_skips_if_no_token(self) -> None:
        """Test that ZenhubEnricher skips if no token is configured."""
        enricher = ZenhubEnricher(
            zenhub_client=AsyncMock(),
            github_client=AsyncMock(),
            zenhub_token=None
        )
        payload = {'organization': 'testorg'}

        result = await enricher.enrich(payload)

        # Should return original payload
        assert result == payload
        assert 'zenhub_issue' not in result

    @pytest.mark.asyncio
    async def test_enrich_skips_if_missing_workspace_id(
        self,
        zenhub_enricher: ZenhubEnricher
    ) -> None:
        """Test that ZenhubEnricher skips if workspace_id is missing."""
        payload = {
            'organization': 'testorg',
            'repo': 'testrepo',
            'issue_number': '123'
            # Missing workspace_id
        }

        result = await zenhub_enricher.enrich(payload)

        # Should return original payload
        assert result == payload
        assert 'zenhub_issue' not in result
