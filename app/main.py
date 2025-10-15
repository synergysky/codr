from fastapi import FastAPI, Request, HTTPException, Depends
from .config import Settings, get_settings
from .github_client import repository_dispatch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zenhub → GitHub Automation", version="0.1.0")

@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "mode": settings.MODE,
        "repos": settings.get_repos(),
        "workspaces": settings.get_workspace_ids(),
    }

@app.post("/webhook/zenhub")
async def zenhub_webhook(request: Request, settings: Settings = Depends(get_settings)):
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

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="invalid json")

    logger.info(f"Received Zenhub webhook: {payload.get('type', 'unknown')}")

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
