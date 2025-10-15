# Zenhub → GitHub Automation Bot

Automatically creates branches and draft pull requests when issues are moved to "In Progress" in Zenhub.

## Architecture

**Relay mode** (default):
1. Zenhub webhook → FastAPI service (Railway)
2. Service validates token and forwards to GitHub `repository_dispatch`
3. GitHub Action in each repo creates branch + draft PR

**Direct mode** (future):
- Service creates branch and PR directly via GitHub API

## Features

- ✅ Multi-repo support (comma-separated `GITHUB_REPOS`)
- ✅ Multi-workspace support (Zenhub workspaces)
- ✅ Pydantic 2 config with validation
- ✅ Docker container with healthcheck
- ✅ Railway-ready (auto PORT binding)
- 🚧 Branch naming: `feature/{issue-number}-{slug}` or `hotfix/{issue-number}-{slug}`
- 🚧 Draft PR with Zenhub metadata
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

## Zenhub Webhook Setup

1. Go to Zenhub → Workspace Settings → Webhooks
2. Add webhook:
   - **URL**: `https://your-app.up.railway.app/webhook/zenhub?token=<WEBHOOK_TOKEN>`
   - **Events**: Select "Issue transferred" or all events
3. Save

**Security note**: The `?token=` query param authenticates the webhook. Alternatively, send as header `x-webhook-token: <WEBHOOK_TOKEN>`.

## GitHub Action Setup

Add this workflow to each repo in `GITHUB_REPOS`:

`.github/workflows/zenhub-automation.yml`:

```yaml
name: Zenhub → Draft PR

on:
  repository_dispatch:
    types: [zenhub_in_progress]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  create-branch-and-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Inspect payload
        run: |
          echo "Zenhub event received"
          echo '${{ toJson(github.event.client_payload) }}'

      # TODO: Add steps to:
      # 1. Parse issue number and title from payload
      # 2. Determine base branch (develop/hotfix/release)
      # 3. Create branch via GitHub API
      # 4. Create draft PR with metadata
```

## Roadmap

- [x] Pydantic 2 config with multi-repo support
- [x] Docker + Railway deployment
- [x] Webhook relay to `repository_dispatch`
- [ ] Parse Zenhub "moved to In Progress" events
- [ ] GitHub Action to create branch + draft PR
- [ ] Idempotency (skip if branch/PR exists)
- [ ] PR body template with Zenhub metadata
- [ ] Direct mode (GitHub App with JWT)
- [ ] Release notes generation

## License

MIT
