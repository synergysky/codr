# GitHub Actions Workflows

This directory contains CI/CD workflows for the Codr project.

## Workflows

### 1. PR Checks (`pr-checks.yml`)
**Trigger:** Pull requests to `develop` or `main`

**Purpose:** Validate PR quality before merge

**Steps:**
- Validate branch naming convention (`feature/*`, `hotfix/*`, etc.)
- Validate PR title format (`feat:`, `fix:`, etc.)
- Run linting (ruff, mypy)
- Run tests with coverage requirement (80%)
- Post coverage report as PR comment

**Required for merge:** ✅ Must pass

---

### 2. Test (`test.yml`)
**Trigger:** Push to `develop` or `main`, or PRs

**Purpose:** Run full test suite

**Steps:**
- Set up Python 3.11
- Install dependencies
- Run linting
- Run tests with coverage
- Upload coverage to Codecov (on PRs)

---

### 3. Docker Build (`docker-build.yml`)
**Trigger:** PRs and pushes to `develop`/`main`

**Purpose:** Validate Docker image builds correctly

**Steps:**
- Build Docker image with BuildKit
- Use GitHub Actions cache for layers
- Test image by importing config module

---

### 4. Deploy to Railway (`deploy-railway.yml`)
**Trigger:** 
- Push to `develop` → deploys to dev environment
- Push to `main` → deploys to production environment
- Manual trigger via `workflow_dispatch`

**Purpose:** Automated deployment to Railway

**Steps:**
- Install Railway CLI
- Link to correct Railway project (dev or prod)
- Deploy with `railway up --detach`
- Post deployment summary

**Required Secrets:**
- `RAILWAY_TOKEN` - Railway API token
- `RAILWAY_PROJECT_ID_DEV` - Dev project ID
- `RAILWAY_PROJECT_ID_PROD` - Production project ID

---

## Setting Up Secrets

### Railway Token
1. Go to [Railway Dashboard](https://railway.app)
2. Click your profile → Account Settings
3. Go to "Tokens" tab
4. Create new token with appropriate permissions
5. Copy token value

### Railway Project IDs
1. Open your Railway project
2. Go to Settings
3. Copy the Project ID (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
4. Repeat for both dev and production projects

### Add to GitHub
1. Go to your GitHub repo
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret:
   - Name: `RAILWAY_TOKEN`, Value: `<your-token>`
   - Name: `RAILWAY_PROJECT_ID_DEV`, Value: `<dev-project-id>`
   - Name: `RAILWAY_PROJECT_ID_PROD`, Value: `<prod-project-id>`

---

## Workflow Diagram

```
┌─────────────────┐
│  Feature Branch │
└────────┬────────┘
         │
         ├─ Push
         │  └─► PR Checks (validate + test)
         │
         ├─ Create PR
         │  └─► Test + Docker Build
         │
         ├─ Merge to develop
         │  └─► Deploy to Railway (dev)
         │
         └─ Merge to main
            └─► Deploy to Railway (prod)
```

---

## Local Testing

Test workflows locally with [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run PR checks
act pull_request -W .github/workflows/pr-checks.yml

# Run tests
act push -W .github/workflows/test.yml

# Run Docker build
act push -W .github/workflows/docker-build.yml
```

---

## Troubleshooting

### Tests fail with "GITHUB_TOKEN is not set"
The test workflow sets required env vars. If running locally, create a `.env` file or export them:
```bash
export GITHUB_TOKEN=test_token
export GITHUB_REPOS=testorg/repo1
export WEBHOOK_TOKEN=test_secret
```

### Railway deployment fails
1. Verify secrets are set correctly in GitHub
2. Check Railway token has not expired
3. Verify project IDs are correct
4. Check Railway project has required env vars set

### Docker build fails
1. Ensure Dockerfile is valid
2. Check all dependencies are in `requirements.txt`
3. Verify base image is accessible

---

## Best Practices

1. **Always create PRs from feature branches** - Never commit directly to `develop` or `main`
2. **Wait for checks to pass** - Don't merge PRs with failing checks
3. **Review coverage reports** - Maintain >80% coverage
4. **Test locally first** - Run `make test` before pushing
5. **Use conventional commits** - Helps with automated changelogs
