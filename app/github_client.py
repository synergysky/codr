import httpx
from .config import settings


async def repository_dispatch(owner: str, repo: str, event_type: str, client_payload: dict) -> None:
    if not settings.GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is not set")
    url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
    headers = {
        "Authorization": f"token {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "zenhub-bot/relay",
    }
    data = {"event_type": event_type, "client_payload": client_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
