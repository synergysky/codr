import httpx


async def get_issue_data(
    workspace_id: str, repo_id: int, issue_number: int, zenhub_token: str
) -> dict:
    """Fetch issue data from Zenhub API.

    Args:
        workspace_id: Zenhub workspace ID
        repo_id: GitHub repository ID
        issue_number: Issue number
        zenhub_token: Zenhub API token

    Returns:
        Dict with Zenhub issue data including estimate, pipeline, epic info

    Raises:
        RuntimeError: If zenhub_token is not provided
        httpx.HTTPStatusError: If Zenhub API returns an error
    """
    if not zenhub_token:
        raise RuntimeError("ZENHUB_TOKEN is not set")

    url = f"https://api.zenhub.com/v5/workspaces/{workspace_id}/repositories/{repo_id}/issues/{issue_number}"
    headers = {
        "X-Authentication-Token": zenhub_token,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def get_issue_events(
    workspace_id: str, repo_id: int, issue_number: int, zenhub_token: str
) -> list[dict]:
    """Fetch issue events from Zenhub API.

    Args:
        workspace_id: Zenhub workspace ID
        repo_id: GitHub repository ID
        issue_number: Issue number
        zenhub_token: Zenhub API token

    Returns:
        List of issue events (transfers, estimates, etc.)

    Raises:
        RuntimeError: If zenhub_token is not provided
        httpx.HTTPStatusError: If Zenhub API returns an error
    """
    if not zenhub_token:
        raise RuntimeError("ZENHUB_TOKEN is not set")

    url = f"https://api.zenhub.com/v5/workspaces/{workspace_id}/repositories/{repo_id}/issues/{issue_number}/events"
    headers = {
        "X-Authentication-Token": zenhub_token,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
