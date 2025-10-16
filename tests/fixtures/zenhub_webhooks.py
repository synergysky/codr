"""Fixtures for Zenhub webhook payloads.

Based on Zenhub webhook documentation:
https://developers.zenhub.com/api-reference/webhooks
"""


def issue_transfer_to_in_progress() -> dict:
    """Zenhub webhook when issue is moved to In Progress pipeline."""
    return {
        "type": "issue_transfer",
        "github_url": "https://api.github.com/repos/testorg/testrepo/issues/123",
        "organization": "testorg",
        "repo": "testrepo",
        "user_name": "testuser",
        "issue_number": "123",
        "issue_title": "Add new feature for user authentication",
        "to_pipeline_name": "In Progress",
        "from_pipeline_name": "Backlog",
        "to_position": "0",
        "workspace_id": "workspace123",
        "workspace_name": "Main Workspace",
    }


def issue_transfer_to_done() -> dict:
    """Zenhub webhook when issue is moved to Done pipeline."""
    return {
        "type": "issue_transfer",
        "github_url": "https://api.github.com/repos/testorg/testrepo/issues/456",
        "organization": "testorg",
        "repo": "testrepo",
        "user_name": "testuser",
        "issue_number": "456",
        "issue_title": "Fix bug in payment processing",
        "to_pipeline_name": "Done",
        "from_pipeline_name": "In Progress",
        "to_position": "0",
        "workspace_id": "workspace123",
        "workspace_name": "Main Workspace",
    }


def issue_comment() -> dict:
    """Zenhub webhook for issue comment (should not trigger PR creation)."""
    return {
        "type": "issue_comment",
        "github_url": "https://api.github.com/repos/testorg/testrepo/issues/789",
        "organization": "testorg",
        "repo": "testrepo",
        "user_name": "testuser",
        "issue_number": "789",
        "comment_id": "comment123",
    }


def github_issue_with_assignees() -> dict:
    """GitHub issue data with assignees."""
    return {
        "id": 123456789,
        "number": 123,
        "title": "Add new feature for user authentication",
        "body": "We need to add OAuth2 authentication support.\n\n## Requirements\n- Google login\n- GitHub login\n- Facebook login",
        "state": "open",
        "html_url": "https://github.com/testorg/testrepo/issues/123",
        "labels": [
            {"name": "enhancement", "color": "84b6eb"},
            {"name": "priority:high", "color": "d93f0b"},
        ],
        "assignees": [
            {"login": "developer1", "id": 111, "avatar_url": "https://github.com/developer1.png"},
            {"login": "developer2", "id": 222, "avatar_url": "https://github.com/developer2.png"},
        ],
        "milestone": {"title": "v2.0", "number": 5},
    }


def github_issue_without_assignees() -> dict:
    """GitHub issue data without assignees (should not trigger PR creation)."""
    return {
        "id": 987654321,
        "number": 456,
        "title": "Fix bug in payment processing",
        "body": "Payment fails when using special characters in address.",
        "state": "open",
        "html_url": "https://github.com/testorg/testrepo/issues/456",
        "labels": [{"name": "bug", "color": "d73a4a"}],
        "assignees": [],
        "milestone": None,
    }


def zenhub_issue_data() -> dict:
    """Zenhub issue data with estimate."""
    return {
        "estimate": {"value": 8},
        "pipeline": {"name": "In Progress", "pipeline_id": "pipeline123"},
        "is_epic": False,
    }


def enriched_payload_ready_for_pr() -> dict:
    """Fully enriched payload that should trigger PR creation."""
    zenhub_webhook = issue_transfer_to_in_progress()
    github_issue = github_issue_with_assignees()
    zenhub_data = zenhub_issue_data()

    return {
        **zenhub_webhook,
        "github_issue": github_issue,
        "zenhub_issue": zenhub_data,
    }


def enriched_payload_no_assignees() -> dict:
    """Enriched payload without assignees (should skip PR creation)."""
    zenhub_webhook = issue_transfer_to_in_progress()
    github_issue = github_issue_without_assignees()
    zenhub_data = zenhub_issue_data()

    return {
        **zenhub_webhook,
        "github_issue": github_issue,
        "zenhub_issue": zenhub_data,
    }
