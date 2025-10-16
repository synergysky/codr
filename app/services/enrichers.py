"""Issue data enrichers."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class GitHubEnricher:
    """Enriches payload with GitHub issue data.

    Follows Single Responsibility Principle:
    - Only responsible for fetching and formatting GitHub data
    - Doesn't know about Zenhub or webhooks
    """

    def __init__(self, github_client: Any):
        """Initialize with GitHub client.

        Args:
            github_client: Client for GitHub API calls
        """
        self.github_client = github_client

    async def enrich(self, payload: dict) -> dict:
        """Enrich payload with GitHub issue data.

        Args:
            payload: Webhook payload

        Returns:
            Payload with 'github_issue' key added
        """
        owner = payload.get('organization')
        repo = payload.get('repo')
        issue_number = payload.get('issue_number')

        # Skip if required data is missing
        if not all([owner, repo, issue_number]):
            logger.debug("Skipping GitHub enrichment: missing required fields")
            return payload

        # Handle list values from parse_qs
        owner_str = owner if isinstance(owner, str) else owner[0]  # type: ignore[index]
        repo_str = repo if isinstance(repo, str) else repo[0]  # type: ignore[index]
        issue_num_str = issue_number if isinstance(issue_number, str) else issue_number[0]  # type: ignore[index]

        try:
            issue_data = await self.github_client.get_issue_details(
                owner_str,
                repo_str,
                int(issue_num_str)
            )

            # Format and add to payload
            enriched = payload.copy()
            enriched['github_issue'] = {
                'title': issue_data.get('title'),
                'body': issue_data.get('body'),
                'labels': [label['name'] for label in issue_data.get('labels', [])],
                'state': issue_data.get('state'),
                'html_url': issue_data.get('html_url'),
                'assignees': [a['login'] for a in issue_data.get('assignees', [])],
                'milestone': issue_data.get('milestone', {}).get('title') if issue_data.get('milestone') else None,
            }

            logger.info(f"Enriched with GitHub data: {len(enriched['github_issue']['labels'])} labels")
            return enriched

        except Exception as e:
            logger.warning(f"Failed to enrich with GitHub data: {e}")
            return payload


class ZenhubEnricher:
    """Enriches payload with Zenhub issue data.

    Follows Single Responsibility Principle:
    - Only responsible for fetching and formatting Zenhub data
    - Doesn't know about GitHub or webhooks
    """

    def __init__(
        self,
        zenhub_client: Any,
        github_client: Any,
        zenhub_token: str | None
    ):
        """Initialize with Zenhub and GitHub clients.

        Args:
            zenhub_client: Client for Zenhub API calls
            github_client: Client for GitHub API calls (to get repo ID)
            zenhub_token: Zenhub API token (optional)
        """
        self.zenhub_client = zenhub_client
        self.github_client = github_client
        self.zenhub_token = zenhub_token

    async def enrich(self, payload: dict) -> dict:
        """Enrich payload with Zenhub issue data.

        Args:
            payload: Webhook payload

        Returns:
            Payload with 'zenhub_issue' key added
        """
        # Skip if no token configured
        if not self.zenhub_token:
            logger.debug("Skipping Zenhub enrichment: no token configured")
            return payload

        owner = payload.get('organization')
        repo = payload.get('repo')
        issue_number = payload.get('issue_number')
        workspace_id = payload.get('workspace_id')

        # Skip if required data is missing
        if not all([owner, repo, issue_number, workspace_id]):
            logger.debug("Skipping Zenhub enrichment: missing required fields")
            return payload

        # Handle list values from parse_qs
        owner_str = owner if isinstance(owner, str) else owner[0]  # type: ignore[index]
        repo_str = repo if isinstance(repo, str) else repo[0]  # type: ignore[index]
        issue_num_str = issue_number if isinstance(issue_number, str) else issue_number[0]  # type: ignore[index]
        workspace_id_str = workspace_id if isinstance(workspace_id, str) else workspace_id[0]  # type: ignore[index]

        try:
            # Get GitHub repo ID
            repo_id = await self.github_client.get_repository_id(owner_str, repo_str)

            # Get Zenhub issue data
            zenhub_data = await self.zenhub_client.get_issue_data(
                workspace_id_str,
                repo_id,
                int(issue_num_str)
            )

            # Format and add to payload
            enriched = payload.copy()
            enriched['zenhub_issue'] = {
                'estimate': zenhub_data.get('estimate', {}).get('value'),
                'pipeline': zenhub_data.get('pipeline', {}).get('name'),
                'is_epic': zenhub_data.get('is_epic', False),
                'epic': zenhub_data.get('epic'),
            }

            logger.info(f"Enriched with Zenhub data: estimate={enriched['zenhub_issue']['estimate']}")
            return enriched

        except Exception as e:
            logger.warning(f"Failed to enrich with Zenhub data: {e}")
            return payload
