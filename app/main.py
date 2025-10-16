import logging
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, HTTPException, Request

from .config import Settings, get_settings
from .github_client import get_issue_details, repository_dispatch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zenhub → GitHub Automation", version="0.1.0")

@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "status": "ok",
        "mode": settings.MODE,
        "repos": settings.get_repos(),
        "workspaces": settings.get_workspace_ids(),
    }

@app.post("/webhook/zenhub")
async def zenhub_webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, object]:
    """
    Receives Zenhub webhook events and dispatches to configured GitHub repos.

    Expected flow:
    1. Validate webhook token
    2. Parse Zenhub payload
    3. Filter for "moved to In Progress" events
    4. Send repository_dispatch to all configured repos
    """
    # Simple token check via header or query param
    token = request.headers.get("x-webhook-token") or request.query_params.get("token")
    if token != settings.WEBHOOK_TOKEN:
        logger.warning("Unauthorized webhook attempt")
        raise HTTPException(status_code=401, detail="unauthorized")

    # Parse payload (Zenhub sends form-encoded data, not JSON)
    body = await request.body()

    if not body:
        logger.info("Received webhook ping (empty body)")
        return {"ok": True, "message": "pong"}

    # Parse form data
    try:
        # Decode form data
        form_data = parse_qs(body.decode('utf-8'))
        # Convert from {'key': ['value']} to {'key': 'value'}
        payload = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
    except Exception as e:
        logger.error(f"Failed to parse form data: {e}")
        logger.error(f"Body content: {body!r}")
        raise HTTPException(status_code=400, detail="invalid payload")

    logger.info(f"Received Zenhub webhook: {payload.get('type', 'unknown')}")
    logger.info(f"Full payload: {payload}")

    # Enrich with GitHub issue data (labels, body, etc.)
    owner = payload.get('organization')
    repo = payload.get('repo')
    issue_number = payload.get('issue_number')

    if owner and repo and issue_number:
        # Ensure values are strings (not lists from parse_qs)
        owner_str = owner if isinstance(owner, str) else owner[0]
        repo_str = repo if isinstance(repo, str) else repo[0]
        issue_num_str = issue_number if isinstance(issue_number, str) else issue_number[0]

        try:
            issue_data = await get_issue_details(owner_str, repo_str, int(issue_num_str), settings.GITHUB_TOKEN)
            # Add GitHub issue details to payload
            payload['github_issue'] = {  # type: ignore[assignment]
                'title': issue_data.get('title'),
                'body': issue_data.get('body'),
                'labels': [label['name'] for label in issue_data.get('labels', [])],
                'state': issue_data.get('state'),
                'html_url': issue_data.get('html_url'),
                'assignees': [a['login'] for a in issue_data.get('assignees', [])],
                'milestone': issue_data.get('milestone', {}).get('title') if issue_data.get('milestone') else None,
            }
            github_issue = payload.get('github_issue')
            labels: list[str] = github_issue.get('labels', []) if isinstance(github_issue, dict) else []
            logger.info(f"Enriched with GitHub issue data: labels={labels}")
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub issue details: {e}")
            # Continue without enrichment

    # TODO: Filter for specific event types (e.g., issue.transfer, pipeline move)
    # For now, forward all events to repos

    repos = settings.get_repos()
    if not repos:
        raise HTTPException(status_code=500, detail="No repos configured")

    results = []
    for repo_full in repos:
        owner, repo = repo_full.split("/", 1)
        try:
            await repository_dispatch(owner, repo, settings.DISPATCH_EVENT, {"zenhub": payload}, settings.GITHUB_TOKEN)
            results.append({"repo": repo_full, "status": "dispatched"})
            logger.info(f"Dispatched to {repo_full}")
        except Exception as e:
            logger.error(f"Failed to dispatch to {repo_full}: {e}")
            results.append({"repo": repo_full, "status": "failed", "error": str(e)})

    return {"ok": True, "results": results}
