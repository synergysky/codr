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


async def get_default_branch(owner: str, repo: str, github_token: str) -> str:
    """Get the default branch of a repository.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        github_token: GitHub authentication token

    Returns:
        Default branch name (e.g., 'main', 'develop')

    Raises:
        RuntimeError: If github_token is not provided
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
        return data["default_branch"]  # type: ignore[no-any-return]


async def create_branch(
    owner: str, repo: str, branch_name: str, base_branch: str, github_token: str
) -> dict:
    """Create a new branch from a base branch.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        branch_name: Name for the new branch
        base_branch: Branch to create from
        github_token: GitHub authentication token

    Returns:
        Dict with branch data

    Raises:
        RuntimeError: If github_token is not provided
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        # Get the SHA of the base branch
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
        ref_resp = await client.get(ref_url, headers=headers)
        ref_resp.raise_for_status()
        base_sha = ref_resp.json()["object"]["sha"]

        # Create the new branch
        create_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        data = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
        create_resp = await client.post(create_url, headers=headers, json=data)
        create_resp.raise_for_status()
        return create_resp.json()  # type: ignore[no-any-return]


async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str,
    draft: bool,
    github_token: str,
) -> dict:
    """Create a pull request.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        title: PR title
        head: Branch containing changes
        base: Branch to merge into
        body: PR description
        draft: Whether to create as draft PR
        github_token: GitHub authentication token

    Returns:
        Dict with PR data

    Raises:
        RuntimeError: If github_token is not provided
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }
    data = {"title": title, "head": head, "base": base, "body": body, "draft": draft}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def create_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str,
    github_token: str,
) -> dict:
    """Create a file in a repository via GitHub API.

    Args:
        owner: Repository owner (org or user)
        repo: Repository name
        path: Path where to create the file (e.g., ".github/ISSUE_123.md")
        content: File content (will be base64 encoded)
        message: Commit message
        branch: Branch to commit to
        github_token: GitHub authentication token

    Returns:
        Dict with commit data

    Raises:
        RuntimeError: If github_token is not provided
        httpx.HTTPStatusError: If GitHub API returns an error
    """
    import base64

    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/direct",
    }

    # Base64 encode the content
    content_bytes = content.encode("utf-8")
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")

    data = {"message": message, "content": content_b64, "branch": branch}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.put(url, headers=headers, json=data)
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
