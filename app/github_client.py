import httpx


async def get_repository_id(owner: str, repo: str, github_token: str) -> int:
    """Fetch repository ID from GitHub API.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        github_token: GitHub authentication token

    Returns:
        Repository ID

    Raises:
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]  # type: ignore[no-any-return]


async def get_issue_details(owner: str, repo: str, issue_number: int, github_token: str) -> dict:
    """Fetch issue details from GitHub API.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        issue_number: Issue number
        github_token: GitHub authentication token

    Returns:
        Dict with issue data including labels, body, title, etc.

    Raises:
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def repository_dispatch(
    owner: str, repo: str, event_type: str, client_payload: dict, github_token: str
) -> None:
    """Send repository_dispatch event to GitHub.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        event_type: Custom event type for workflow trigger
        client_payload: Payload data to send
        github_token: GitHub authentication token

    Raises:
        RuntimeError: If github_token is not provided
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }
    data = {"event_type": event_type, "client_payload": client_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
