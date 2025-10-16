"""Service for creating branches and PRs when issues move to In Progress."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PRService:
    """Handles automatic branch and PR creation for issues.

    Follows Single Responsibility Principle:
    - Only responsible for PR/branch creation logic
    - Uses dependency injection for GitHub client
    """

    def __init__(self, github_client: Any, github_token: str, base_branch: str = "develop"):
        """Initialize PR service.

        Args:
            github_client: GitHub client module with API functions
            github_token: GitHub authentication token
            base_branch: Default branch to create PRs against
        """
        self.github_client = github_client
        self.github_token = github_token
        self.base_branch = base_branch

    def _should_create_pr(self, payload: dict) -> bool:
        """Check if PR should be created based on webhook payload.

        Args:
            payload: Enriched webhook payload

        Returns:
            True if PR should be created
        """
        # Check if it's an issue transfer event or GitHub assigned event
        # Zenhub: "issue.transfer" or "issue_transfer"
        # GitHub: "github_assigned"
        event_type = payload.get("type", "")
        valid_events = ["issue.transfer", "issue_transfer", "github_assigned"]
        if event_type not in valid_events:
            logger.info(
                f"Skipping PR creation: event type is '{event_type}' "
                f"(expected one of: {', '.join(valid_events)})"
            )
            return False

        # Check if issue is in "In Progress"
        # For Zenhub transfer events: use to_pipeline_name
        # For GitHub assigned events: use zenhub_issue.pipeline.name
        to_pipeline = payload.get("to_pipeline_name", "")
        if not to_pipeline:
            # GitHub assigned event - check current pipeline from Zenhub data
            zenhub_issue = payload.get("zenhub_issue", {})
            to_pipeline = zenhub_issue.get("pipeline", {}).get("name", "")

        if to_pipeline.lower() != "in progress":
            logger.info(
                f"Skipping PR creation: pipeline is '{to_pipeline}' (expected 'In Progress')"
            )
            return False

        # Check if issue has assignees
        github_issue = payload.get("github_issue", {})
        assignees = github_issue.get("assignees", [])
        if not assignees:
            logger.info("Skipping PR creation: no assignees")
            return False

        logger.info("✅ All conditions met for PR creation!")
        return True

    def _generate_branch_name(self, issue_number: int, title: str) -> str:
        """Generate branch name from issue number and title.

        Args:
            issue_number: GitHub issue number
            title: Issue title

        Returns:
            Branch name (e.g., 'feature/123-add-new-feature')
        """
        # Sanitize title for branch name
        sanitized = title.lower()
        # Remove non-ASCII characters and keep only alphanumeric, spaces, and hyphens
        sanitized = "".join(
            c if (c.isalnum() and ord(c) < 128) or c in " -" else "" for c in sanitized
        )
        sanitized = "-".join(sanitized.split())[:50]  # Limit length

        return f"feature/{issue_number}-{sanitized}"

    def _generate_pr_body(self, payload: dict) -> str:
        """Generate PR description from issue data.

        Args:
            payload: Enriched webhook payload

        Returns:
            PR body with issue context
        """
        github_issue = payload.get("github_issue", {})
        zenhub_issue = payload.get("zenhub_issue", {})

        lines = []

        # Link to issue
        issue_url = github_issue.get("html_url", "")
        issue_number = payload.get("issue_number", "")
        if issue_url:
            lines.append(f"Closes #{issue_number}")
            lines.append("")

        # Issue description
        body = github_issue.get("body", "")
        if body:
            lines.append("## Issue Description")
            lines.append(body)
            lines.append("")

        # Labels
        labels = github_issue.get("labels", [])
        if labels:
            label_names = []
            for label in labels:
                if isinstance(label, dict) and "name" in label:
                    label_names.append(label["name"])
                elif isinstance(label, str):
                    label_names.append(label)
            if label_names:
                lines.append("## Labels")
                lines.append(", ".join(f"`{label}`" for label in label_names))
                lines.append("")

        # Zenhub info
        estimate_data = zenhub_issue.get("estimate")
        estimate = None
        if isinstance(estimate_data, dict):
            estimate = estimate_data.get("value")
        elif isinstance(estimate_data, (int, float)):
            estimate = estimate_data
        if estimate:
            lines.append(f"**Estimate:** {estimate} points")
            lines.append("")

        # Assignees
        assignees = github_issue.get("assignees", [])
        if assignees:
            assignee_logins = []
            for a in assignees:
                if isinstance(a, dict):
                    login = a.get("login")
                    if login:
                        assignee_logins.append(login)
                elif isinstance(a, str):
                    assignee_logins.append(a)
            if assignee_logins:
                lines.append("## Assignees")
                lines.append(", ".join(f"@{login}" for login in assignee_logins))
                lines.append("")

        # Milestone
        milestone = github_issue.get("milestone")
        if milestone:
            milestone_title = (
                milestone.get("title") if isinstance(milestone, dict) else str(milestone)
            )
            lines.append(f"**Milestone:** {milestone_title}")
            lines.append("")

        return "\n".join(lines)

    def _generate_context_file(self, payload: dict, issue_number: int) -> str:
        """Generate markdown file with all issue context from GitHub and Zenhub.

        Args:
            payload: Enriched webhook payload with GitHub and Zenhub data
            issue_number: Issue number

        Returns:
            Markdown content with all available context
        """
        from datetime import UTC, datetime

        lines = []
        github_issue = payload.get("github_issue", {})
        zenhub_issue = payload.get("zenhub_issue", {})

        # Header
        title = github_issue.get("title", "Untitled")
        lines.append(f"# Issue #{issue_number}: {title}")
        lines.append("")
        lines.append(f"**Moved to In Progress:** {datetime.now(UTC).isoformat()}")
        lines.append("")

        # GitHub metadata
        lines.append("## GitHub Metadata")
        lines.append("")
        lines.append(f"- **URL:** {github_issue.get('html_url', 'N/A')}")
        lines.append(f"- **State:** {github_issue.get('state', 'N/A')}")
        lines.append(f"- **Created:** {github_issue.get('created_at', 'N/A')}")
        lines.append(f"- **Updated:** {github_issue.get('updated_at', 'N/A')}")
        lines.append("")

        # Labels
        labels = github_issue.get("labels", [])
        if labels:
            label_names = []
            for label in labels:
                if isinstance(label, dict):
                    label_names.append(f"`{label.get('name', 'unknown')}`")
                elif isinstance(label, str):
                    label_names.append(f"`{label}`")
            if label_names:
                lines.append(f"**Labels:** {', '.join(label_names)}")
                lines.append("")

        # Assignees
        assignees = github_issue.get("assignees", [])
        if assignees:
            assignee_names = []
            for assignee in assignees:
                if isinstance(assignee, dict):
                    assignee_names.append(f"@{assignee.get('login', 'unknown')}")
                elif isinstance(assignee, str):
                    assignee_names.append(f"@{assignee}")
            if assignee_names:
                lines.append(f"**Assignees:** {', '.join(assignee_names)}")
                lines.append("")

        # Milestone
        milestone = github_issue.get("milestone")
        if milestone:
            milestone_title = milestone.get("title") if isinstance(milestone, dict) else milestone
            if milestone_title:
                lines.append(f"**Milestone:** {milestone_title}")
                lines.append("")

        # Zenhub metadata
        if zenhub_issue:
            lines.append("## Zenhub Metadata")
            lines.append("")

            estimate = zenhub_issue.get("estimate")
            if estimate is not None:
                estimate_value = estimate.get("value") if isinstance(estimate, dict) else estimate
                if estimate_value is not None:
                    lines.append(f"**Estimate:** {estimate_value} points")
                    lines.append("")

            pipeline = zenhub_issue.get("pipeline", {})
            if isinstance(pipeline, dict):
                pipeline_name = pipeline.get("name")
                if pipeline_name:
                    lines.append(f"**Pipeline:** {pipeline_name}")
                    lines.append("")

            epic = zenhub_issue.get("epic")
            if epic:
                epic_number = epic.get("issue_number") if isinstance(epic, dict) else None
                if epic_number:
                    lines.append(f"**Epic:** #{epic_number}")
                    lines.append("")

        # Issue body/description
        body = github_issue.get("body", "")
        if body and body.strip():
            lines.append("## Issue Description")
            lines.append("")
            lines.append(body)
            lines.append("")

        # Webhook metadata
        lines.append("---")
        lines.append("")
        lines.append("## Automation Metadata")
        lines.append("")
        lines.append(f"- **Workflow:** {payload.get('type', 'unknown')}")
        lines.append(
            f"- **Repository:** {payload.get('organization', 'N/A')}/{payload.get('repo', 'N/A')}"
        )
        lines.append(f"- **Workspace:** {payload.get('workspace_name', 'N/A')}")
        lines.append(f"- **From Pipeline:** {payload.get('from_pipeline_name', 'N/A')}")
        lines.append(f"- **To Pipeline:** {payload.get('to_pipeline_name', 'N/A')}")
        lines.append("")
        lines.append(
            "*This file was auto-generated by zenhub-bot when the issue was moved to 'In Progress'.*"
        )

        return "\n".join(lines)

    async def handle_issue_moved(self, payload: dict, owner: str, repo: str) -> dict | None:
        """Handle issue moved to In Progress - create branch and draft PR.

        Args:
            payload: Enriched webhook payload
            owner: Repository owner
            repo: Repository name

        Returns:
            Dict with PR info if created, None if skipped
        """
        if not self._should_create_pr(payload):
            return None

        github_issue = payload.get("github_issue", {})
        issue_number = int(payload.get("issue_number", 0))
        title = github_issue.get("title", f"Issue #{issue_number}")

        try:
            # Generate branch name
            branch_name = self._generate_branch_name(issue_number, title)
            logger.info(f"Creating branch: {branch_name}")

            # Create branch from base branch
            await self.github_client.create_branch(
                owner, repo, branch_name, self.base_branch, self.github_token
            )

            # Create initial commit with issue context
            context_file_content = self._generate_context_file(payload, issue_number)
            context_file_path = f".github/ISSUE_{issue_number}.md"
            logger.info(f"Creating context file: {context_file_path}")

            await self.github_client.create_file(
                owner=owner,
                repo=repo,
                path=context_file_path,
                content=context_file_content,
                message=f"chore: add issue context for #{issue_number}",
                branch=branch_name,
                github_token=self.github_token,
            )

            # Generate PR body
            pr_body = self._generate_pr_body(payload)

            # Create draft PR
            pr_title = f"[WIP] {title}"
            logger.info(f"Creating draft PR: {pr_title}")

            pr = await self.github_client.create_pull_request(
                owner=owner,
                repo=repo,
                title=pr_title,
                head=branch_name,
                base=self.base_branch,
                body=pr_body,
                draft=True,
                github_token=self.github_token,
            )

            logger.info(f"✅ Created branch '{branch_name}' and draft PR #{pr['number']}")

            return {
                "branch": branch_name,
                "pr_number": pr["number"],
                "pr_url": pr["html_url"],
            }

        except Exception as e:
            logger.error(f"Failed to create branch/PR: {e}", exc_info=True)
            return None
