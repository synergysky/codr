# GitHub Environments Setup Guide

This guide walks you through setting up GitHub Environments for automated Railway deployment.

## Why Environments?

- **Security:** Separate secrets for dev/prod
- **Protection:** Require approval before prod deployments
- **Visibility:** Track deployment history per environment
- **Control:** Restrict which branches can deploy where

---

## Step-by-Step Setup

### 1. Create Railway Projects

First, create two Railway projects:

1. **Development Project:**
   - Go to [Railway Dashboard](https://railway.app)
   - New Project → Deploy from GitHub
   - Select `synergysky/codr` repo
   - Name it `codr-dev`
   - Note the Project ID (Settings → Project ID)
   - Note the public URL (e.g., `https://codr-dev.up.railway.app`)

2. **Production Project:**
   - Create another project
   - Name it `codr-prod`
   - Note the Project ID
   - Note the public URL (e.g., `https://codr.up.railway.app`)

### 2. Get Railway API Token

1. Go to Railway Dashboard
2. Click your profile → Account Settings
3. Go to "Tokens" tab
4. Click "Create Token"
5. Name it `GitHub Actions`
6. Copy the token (you'll use this for both environments)

### 3. Create GitHub Environments

#### Create Development Environment

1. Go to your GitHub repo: `https://github.com/synergysky/codr`
2. Click **Settings** → **Environments**
3. Click **New environment**
4. Name: `development`
5. Click **Configure environment**

**Configure Development:**
- **Deployment branches:** Select "Selected branches" → Add rule: `develop`
- **Environment secrets:** Click "Add secret"
  - Name: `RAILWAY_TOKEN`, Value: `<your-railway-token>`
  - Name: `RAILWAY_PROJECT_ID`, Value: `<dev-project-id>`
- **Environment variables:** Click "Add variable"
  - Name: `RAILWAY_URL`, Value: `https://codr-dev.up.railway.app`

#### Create Production Environment

1. Back to **Environments** page
2. Click **New environment**
3. Name: `production`
4. Click **Configure environment**

**Configure Production:**
- **Deployment branches:** Select "Selected branches" → Add rule: `main`
- **Environment protection rules:**
  - ✅ Check "Required reviewers"
  - Add yourself as reviewer
  - (Optional) Set wait timer if you want delay before deploy
- **Environment secrets:** Click "Add secret"
  - Name: `RAILWAY_TOKEN`, Value: `<your-railway-token>` (same as dev)
  - Name: `RAILWAY_PROJECT_ID`, Value: `<prod-project-id>`
- **Environment variables:** Click "Add variable"
  - Name: `RAILWAY_URL`, Value: `https://codr.up.railway.app`

---

## Verification

### Test Development Deployment

1. Push a commit to `develop` branch:
   ```bash
   git checkout develop
   git commit --allow-empty -m "test: trigger dev deployment"
   git push origin develop
   ```

2. Go to **Actions** tab in GitHub
3. Watch "Deploy to Railway" workflow
4. Should auto-deploy to development environment
5. Verify at your dev URL: `curl https://codr-dev.up.railway.app/health`

### Test Production Deployment

1. Push a commit to `main` branch (or merge a PR):
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

2. Go to **Actions** tab
3. Workflow will wait for your approval (yellow status)
4. Click on the workflow → Click "Review deployments"
5. Check `production` → Click "Approve and deploy"
6. Verify at prod URL: `curl https://codr.up.railway.app/health`

---

## Environment Variables in Railway

Don't forget to set these in **each Railway project** (not GitHub):

### Required Variables
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPOS=synergysky/repo1,synergysky/repo2
WEBHOOK_TOKEN=your-shared-secret-here
```

### Optional Variables
```
ZENHUB_PIPELINE_NAME=In Progress
BASE_BRANCH_DEFAULT=develop
BASE_BRANCH_HOTFIX=hotfix_branch
HOTFIX_LABEL=hotfix
MODE=relay
DISPATCH_EVENT=zenhub_in_progress
```

---

## Troubleshooting

### Deployment fails with "Environment not found"
- Verify environment names are exactly `development` and `production`
- Check deployment branch rules match your branch names

### "Required reviewers" not working
- Make sure you added yourself as a reviewer in production environment settings
- Check that you have write access to the repo

### Railway deployment fails
- Verify `RAILWAY_TOKEN` is valid and not expired
- Check `RAILWAY_PROJECT_ID` matches the correct project
- Ensure Railway project has all required environment variables set

### Can't see deployment history
- Go to repo → Environments
- Click on environment name
- View deployment history and logs

---

## Best Practices

1. **Never share Railway tokens** - They're sensitive credentials
2. **Use different Railway projects** for dev/prod - Prevents accidental overwrites
3. **Always test in dev first** - Merge to `develop`, verify, then merge to `main`
4. **Review prod deployments** - Don't auto-approve, check what's being deployed
5. **Monitor Railway logs** - Check for errors after deployment

---

## Next Steps

After setup:
1. ✅ Environments configured
2. ✅ Secrets added
3. ✅ Test deployment to dev
4. ✅ Test deployment to prod with approval
5. → Configure Zenhub webhook to point to your Railway URL
6. → Set up monitoring/alerts (optional)
