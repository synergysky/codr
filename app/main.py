import logging
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, HTTPException, Request

from . import github_client, zenhub_client
from .config import Settings, get_settings
from .services.enrichers import GitHubEnricher, ZenhubEnricher
from .services.webhook_service import WebhookService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zenhub → GitHub Automation", version="0.1.0")


# Dependency injection for WebhookService
def get_webhook_service(settings: Settings = Depends(get_settings)) -> WebhookService:
    """Create WebhookService with configured enrichers.

    Follows Dependency Inversion Principle:
    - main.py depends on abstractions (IssueEnricher protocol)
    - Concrete implementations injected here
    """
    from collections.abc import Sequence

    from .services.protocols import IssueEnricher

    enrichers: Sequence[IssueEnricher] = [
        GitHubEnricher(
            github_client=github_client,
            github_token=settings.GITHUB_TOKEN
        ),
        ZenhubEnricher(
            zenhub_client=zenhub_client,
            github_client=github_client,
            github_token=settings.GITHUB_TOKEN,
            zenhub_token=settings.ZENHUB_TOKEN
        )
    ]
    return WebhookService(enrichers=enrichers)

@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "status": "ok",
        "mode": settings.MODE,
        "repos": settings.get_repos(),
        "workspaces": settings.get_workspace_ids(),
    }

@app.post("/webhook/zenhub")
async def zenhub_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    webhook_service: WebhookService = Depends(get_webhook_service)
) -> dict[str, object]:
    """
    Receives Zenhub webhook events and dispatches to configured GitHub repos.

    Refactored to use service layer (SOLID principles):
    - Single Responsibility: main.py only handles HTTP concerns
    - Dependency Inversion: depends on WebhookService abstraction
    """
    # Validate webhook token
    token = request.headers.get("x-webhook-token") or request.query_params.get("token")
    if token != settings.WEBHOOK_TOKEN:
        logger.warning("Unauthorized webhook attempt")
        raise HTTPException(status_code=401, detail="unauthorized")

    # Parse payload (Zenhub sends form-encoded data)
    body = await request.body()

    if not body:
        logger.info("Received webhook ping (empty body)")
        return {"ok": True, "message": "pong"}

    try:
        form_data = parse_qs(body.decode('utf-8'))
        payload = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
    except Exception as e:
        logger.error(f"Failed to parse form data: {e}")
        logger.error(f"Body content: {body!r}")
        raise HTTPException(status_code=400, detail="invalid payload")

    logger.info(f"Received Zenhub webhook: {payload.get('type', 'unknown')}")

    # Enrich payload using service layer
    enriched_payload = await webhook_service.process_webhook(payload)

    # TODO: Filter for specific event types (e.g., issue.transfer, pipeline move)
    # For now, forward all events to repos

    repos = settings.get_repos()
    if not repos:
        raise HTTPException(status_code=500, detail="No repos configured")

    results = []
    for repo_full in repos:
        owner, repo = repo_full.split("/", 1)
        try:
            await github_client.repository_dispatch(
                owner, repo, settings.DISPATCH_EVENT,
                {"zenhub": enriched_payload},
                settings.GITHUB_TOKEN
            )
            results.append({"repo": repo_full, "status": "dispatched"})
            logger.info(f"Dispatched to {repo_full}")
        except Exception as e:
            logger.error(f"Failed to dispatch to {repo_full}: {e}")
            results.append({"repo": repo_full, "status": "failed", "error": str(e)})

    return {"ok": True, "results": results}
