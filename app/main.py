import logging
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, HTTPException, Request

from . import github_client, zenhub_client
from .config import Settings, get_settings
from .services.enrichers import GitHubEnricher, ZenhubEnricher
from .services.pr_service import PRService
from .services.webhook_service import WebhookService

# Setup logging - will be configured on startup
logger = logging.getLogger(__name__)

app = FastAPI(title="Zenhub → GitHub Automation", version="0.1.0")


@app.on_event("startup")
async def configure_logging() -> None:
    """Configure logging level from settings on startup."""
    try:
        settings = get_settings()
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True,  # Override any existing config
        )
        logger.info(f"Logging configured with level: {settings.LOG_LEVEL.upper()}")
    except Exception as e:
        # Fallback to INFO if settings fail
        logging.basicConfig(level=logging.INFO)
        logger.warning(f"Failed to load LOG_LEVEL from settings, using INFO: {e}")


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
        GitHubEnricher(github_client=github_client, github_token=settings.GITHUB_TOKEN),
        ZenhubEnricher(
            zenhub_client=zenhub_client,
            github_client=github_client,
            github_token=settings.GITHUB_TOKEN,
            zenhub_token=settings.ZENHUB_TOKEN,
        ),
    ]
    return WebhookService(enrichers=enrichers)


def get_pr_service(settings: Settings = Depends(get_settings)) -> PRService:
    """Create PRService for handling branch/PR creation.

    Args:
        settings: Application settings

    Returns:
        Configured PRService instance
    """
    return PRService(
        github_client=github_client,
        github_token=settings.GITHUB_TOKEN,
        base_branch="develop",  # TODO: Make configurable per repo
    )


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "status": "ok",
        "mode": settings.MODE,
        "repos": settings.get_repos(),
        "workspaces": settings.get_workspace_ids(),
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    webhook_service: WebhookService = Depends(get_webhook_service),
    pr_service: PRService = Depends(get_pr_service),
) -> dict[str, object]:
    """
    Receives GitHub webhook events (for assignee changes).

    Handles:
    - issues.assigned: When someone is assigned to an issue
    """
    # GitHub uses X-Hub-Signature for validation, but we'll use token for simplicity
    token = request.headers.get("x-webhook-token") or request.query_params.get("token")
    if token != settings.WEBHOOK_TOKEN:
        logger.warning("Unauthorized GitHub webhook attempt")
        raise HTTPException(status_code=401, detail="unauthorized")

    body = await request.body()
    if not body:
        logger.info("Received GitHub webhook ping")
        return {"ok": True, "message": "pong"}

    try:
        import json

        payload = json.loads(body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse GitHub webhook: {e}")
        raise HTTPException(status_code=400, detail="invalid payload")

    event_type = request.headers.get("x-github-event", "unknown")
    logger.info(f"Received GitHub webhook: {event_type}")

    # Only handle issues.assigned event
    if event_type != "issues" or payload.get("action") != "assigned":
        logger.debug(f"Ignoring GitHub event: {event_type}/{payload.get('action')}")
        return {"ok": True, "message": "event ignored"}

    # Extract issue info
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")
    issue_number = issue.get("number")

    if not all([owner, repo_name, issue_number]):
        logger.error("Missing required fields in GitHub webhook")
        return {"ok": False, "error": "missing fields"}

    logger.info(f"Issue #{issue_number} assigned in {owner}/{repo_name}")

    # Enrich with Zenhub data to check pipeline
    fake_zenhub_payload = {
        "type": "github_assigned",
        "organization": owner,
        "repo": repo_name,
        "issue_number": str(issue_number),
        "workspace_id": settings.get_workspace_ids()[0] if settings.get_workspace_ids() else "",
    }

    enriched = await webhook_service.process_webhook(fake_zenhub_payload)

    # Check if issue is in "In Progress" pipeline
    zenhub_issue = enriched.get("zenhub_issue", {})
    pipeline_name = zenhub_issue.get("pipeline", {}).get("name", "")

    if pipeline_name.lower() == "in progress":
        logger.info("Issue in 'In Progress', attempting PR creation")
        pr_result = await pr_service.handle_issue_moved(enriched, owner, repo_name)
        if pr_result:
            logger.info(f"Created PR: {pr_result}")
            return {"ok": True, "pr": pr_result}

    logger.info(f"Issue not in 'In Progress' (pipeline: {pipeline_name}), skipping PR")
    return {"ok": True, "message": "not in progress"}


@app.post("/webhook/zenhub")
async def zenhub_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    webhook_service: WebhookService = Depends(get_webhook_service),
    pr_service: PRService = Depends(get_pr_service),
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
        form_data = parse_qs(body.decode("utf-8"))
        payload = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
    except Exception as e:
        logger.error(f"Failed to parse form data: {e}")
        logger.error(f"Body content: {body!r}")
        raise HTTPException(status_code=400, detail="invalid payload")

    logger.info(f"Received Zenhub webhook: {payload.get('type', 'unknown')}")
    logger.debug(f"Raw payload: {payload}")

    # Enrich payload using service layer
    enriched_payload = await webhook_service.process_webhook(payload)
    logger.debug(f"Enriched payload keys: {list(enriched_payload.keys())}")

    # Handle automatic PR creation for issues moved to In Progress
    pr_result = None
    if enriched_payload.get("organization") and enriched_payload.get("repo"):
        owner = enriched_payload["organization"]
        repo_name = enriched_payload["repo"]
        logger.info(
            f"Attempting PR creation for {owner}/{repo_name}, "
            f"type={enriched_payload.get('type')}, "
            f"to_pipeline={enriched_payload.get('to_pipeline_name')}, "
            f"has_assignees={bool(enriched_payload.get('github_issue', {}).get('assignees'))}"
        )
        pr_result = await pr_service.handle_issue_moved(enriched_payload, owner, repo_name)
        if pr_result:
            logger.info(f"Created PR: {pr_result}")
            # Add PR info to payload for GitHub Actions
            enriched_payload["auto_pr"] = pr_result

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
                owner,
                repo,
                settings.DISPATCH_EVENT,
                {"zenhub": enriched_payload},
                settings.GITHUB_TOKEN,
            )
            results.append({"repo": repo_full, "status": "dispatched"})
            logger.info(f"Dispatched to {repo_full}")
        except Exception as e:
            logger.error(f"Failed to dispatch to {repo_full}: {e}")
            results.append({"repo": repo_full, "status": "failed", "error": str(e)})

    return {"ok": True, "results": results}
