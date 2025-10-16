# Zenhub → GitHub Automation Bot

Automatically creates branches and draft pull requests when issues are moved to "In Progress" in Zenhub **and** when assignees are added to issues already in progress.

## Architecture

**Direct mode** (current):
1. Zenhub webhook → FastAPI service (Railway) → Creates branch + draft PR
2. GitHub webhook → FastAPI service (Railway) → Creates branch + draft PR
3. Service enriches with data from GitHub + Zenhub APIs

**Two triggers for maximum coverage:**
- ✅ **Zenhub webhook** (`/webhook/zenhub`): Issue moved to "In Progress" → Check if has assignees → Create PR
- ✅ **GitHub webhook** (`/webhook/github`): Assignee added to issue → Check if in "In Progress" → Create PR

## Features

- ✅ Multi-repo support (comma-separated `GITHUB_REPOS`)
- ✅ Multi-workspace support (Zenhub workspaces)
- ✅ Webhook security with token validation
- ✅ **GitHub issue enrichment** (labels, body, assignees, milestone)
- ✅ **Zenhub issue enrichment** (estimate, pipeline, epic info)
- ✅ **Automatic branch creation** (`feature/{issue-number}-{sanitized-title}`)
- ✅ **Draft PR with full context** (description, labels, assignees, estimate, milestone)
- ✅ **Dual webhook support** (Zenhub + GitHub)
- ✅ Form-encoded webhook data parsing
- ✅ Pydantic 2 config with validation
- ✅ Docker container with healthcheck
- ✅ Railway-ready (auto PORT binding)
- ✅ 88% test coverage (53 tests: 48 unit + 5 integration)
- ✅ SOLID principles + TDD methodology
- 🚧 Idempotency (skip if branch/PR exists)

## Configuration

All configuration via environment variables (see `.env.example`).

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub PAT or App token with `repo` scope | `ghp_xxx...` |
| `GITHUB_REPOS` | Comma-separated repos (owner/repo) | `myorg/repo1,myorg/repo2` |
| `WEBHOOK_TOKEN` | Shared secret for webhook auth | `supersecret123` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `MODE` | `relay` | `relay` or `direct` |
| `ZENHUB_TOKEN` | - | Zenhub API token (for direct mode) |
| `ZENHUB_WORKSPACE_IDS` | - | Comma-separated workspace IDs |
| `ZENHUB_PIPELINE_NAME` | `In Progress` | Exact pipeline name to trigger on |
| `DISPATCH_EVENT` | `zenhub_in_progress` | GitHub dispatch event type |
| `BASE_BRANCH_DEFAULT` | `develop` | Default base branch |
| `BASE_BRANCH_HOTFIX` | `hotfix_branch` | Base for hotfix issues |
| `HOTFIX_LABEL` | `hotfix` | Label marking hotfix issues |
| `PORT` | `8000` | HTTP port (Railway sets this) |

## Local Development

### Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Using Makefile (Recommended)

```bash
# Show all available commands
make help

# Create venv and install dependencies
make venv
source venv/bin/activate
make install

# Run tests
make test

# Run tests with coverage
make test-cov

# Run linting
make lint

# Run application locally
make run
```

### Build and run with Docker

```bash
# Build
docker build -t zenhub-bot:dev .

# Run (replace values)
docker run --rm -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e GITHUB_REPOS=myorg/repo1 \
  -e WEBHOOK_TOKEN=secret \
  zenhub-bot:dev
```

### Test locally

```bash
# Health check
curl http://localhost:8000/health

# Webhook (with token)
curl -X POST "http://localhost:8000/webhook/zenhub?token=secret" \
  -H "Content-Type: application/json" \
  -d '{"type":"issue.transfer","issue_number":123}'
```

## CI/CD

### GitHub Actions Workflows

The project includes three automated workflows:

1. **Test** (`.github/workflows/test.yml`)
   - Runs on PRs and pushes to `develop`/`main`
   - Executes linting (ruff, mypy)
   - Runs pytest with coverage reporting
   - Uploads coverage to Codecov

2. **Deploy to Railway** (`.github/workflows/deploy-railway.yml`)
   - Auto-deploys `develop` → Railway dev environment
   - Auto-deploys `main` → Railway production environment
   - Manual trigger via `workflow_dispatch`

3. **Docker Build** (`.github/workflows/docker-build.yml`)
   - Validates Docker image builds on PRs
   - Uses Docker layer caching for speed

### Required GitHub Environments

Set up two environments for deployment (Settings → Environments):

#### Development Environment
1. Create environment named `development`
2. Deployment branches: `develop` only
3. Add secrets:
   - `RAILWAY_TOKEN` - Railway API token
   - `RAILWAY_PROJECT_ID` - Dev Railway project ID
4. Add variables:
   - `RAILWAY_URL` - Dev Railway URL

#### Production Environment
1. Create environment named `production`
2. Deployment branches: `main` only
3. **Enable protection rules:**
   - ✅ Required reviewers (add yourself)
4. Add secrets:
   - `RAILWAY_TOKEN` - Railway API token
   - `RAILWAY_PROJECT_ID` - Prod Railway project ID
5. Add variables:
   - `RAILWAY_URL` - Prod Railway URL

## Railway Deployment

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin git@github.com:synergysky/codr.git
git branch -M main
git push -u origin main
```

### 2. Create Railway project

1. Go to [Railway](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Select `zenhub-bot` repo
4. Railway auto-detects Dockerfile

### 3. Set environment variables

In Railway dashboard → Variables, add:

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPOS=myorg/repo1,myorg/repo2
WEBHOOK_TOKEN=your-shared-secret-here
ZENHUB_PIPELINE_NAME=In Progress
```

Optional variables (use defaults or customize):
```
BASE_BRANCH_DEFAULT=develop
BASE_BRANCH_HOTFIX=hotfix_branch
HOTFIX_LABEL=hotfix
```

### 4. Deploy

Railway deploys automatically. Get your public URL from the dashboard (e.g., `https://zenhub-bot-production.up.railway.app`).

### 5. Verify

```bash
curl https://your-app.up.railway.app/health
```

Should return:
```json
{
  "status": "ok",
  "mode": "relay",
  "repos": ["myorg/repo1", "myorg/repo2"],
  "workspaces": []
}
```

## Webhook Setup

You need to configure **TWO webhooks** for full functionality:

### 1. Zenhub Webhook

Triggers when issues are moved between pipelines (e.g., to "In Progress").

1. Go to Zenhub → Workspace Settings → Webhooks
2. Add webhook:
   - **URL**: `https://your-app.up.railway.app/webhook/zenhub?token=<WEBHOOK_TOKEN>`
   - **Events**: Select **all events** (service filters relevant ones; allows future expansion)
3. Save

**Note:** The service currently only acts on `issue_transfer` events to "In Progress", but receiving all events enables easy feature additions later.

### 2. GitHub Webhook

Triggers when assignees are added to issues.

1. Go to GitHub repo → Settings → Webhooks → Add webhook
2. Configure:
   - **Payload URL**: `https://your-app.up.railway.app/webhook/github?token=<WEBHOOK_TOKEN>`
   - **Content type**: `application/json`
   - **Events**: Choose "Let me select individual events"
     - ✅ Issues (all issue events - service filters for `assigned`)
   - **Active**: ✅ Checked
3. Add webhook

**Note:** The service currently only acts on `issues.assigned` events, but receiving all issue events enables easy feature additions later.

**Security note**: The `?token=` query param authenticates the webhook. Alternatively, send as header `x-webhook-token: <WEBHOOK_TOKEN>`.

### Why Both Webhooks?

| Scenario | Trigger | Webhook Source | Result |
|----------|---------|----------------|--------|
| Issue in Backlog → Moved to "In Progress" (already has assignees) | Pipeline change | Zenhub | ✅ PR created |
| Issue in "In Progress" → Assignee added | Assignee change | GitHub | ✅ PR created |
| Issue in Backlog → Assignee added | Assignee change | GitHub | ❌ No PR (not in progress) |
| Issue moved to "Done" | Pipeline change | Zenhub | ❌ No PR (wrong pipeline) |

Without **both** webhooks, you'll miss some scenarios!

## How It Works

When a PR is created, the service:

1. **Enriches issue data** from GitHub API (title, body, labels, assignees, milestone)
2. **Enriches Zenhub data** via Zenhub API (estimate, pipeline, epic info)  
3. **Creates a branch**: `feature/{issue-number}-{sanitized-title}` from `develop`
4. **Creates a draft PR** with complete context:
   ```markdown
   Closes #123
   
   ## Issue Description
   [Full issue body from GitHub]
   
   ## Labels
   `bug`, `priority:high`
   
   **Estimate:** 8 points
   
   ## Assignees
   @developer1, @developer2
   
   **Milestone:** v2.0
   ```

### Example Flow

1. Issue #456 "Add OAuth login" is in Backlog
2. Developer moves it to "In Progress" 
3. Zenhub webhook → Service checks: has assignees? ✅
4. Service creates `feature/456-add-oauth-login` branch
5. Service creates draft PR with full context
6. Developer gets notification about new PR

## Roadmap

- [x] Pydantic 2 config with multi-repo support
- [x] Docker + Railway deployment
- [x] Parse Zenhub "moved to In Progress" events
- [x] GitHub + Zenhub data enrichment
- [x] Automatic branch creation
- [x] Draft PR with full metadata and context
- [x] Dual webhook support (Zenhub + GitHub)
- [x] SOLID principles + TDD (88% test coverage)
- [x] Integration tests with realistic fixtures
- [ ] Idempotency (skip if branch/PR already exists)
- [ ] Configurable base branch per repo (develop/main/release)
- [ ] Support for hotfix workflow (different base branch)
- [ ] PR template customization
- [ ] Release notes generation

## License

MIT
