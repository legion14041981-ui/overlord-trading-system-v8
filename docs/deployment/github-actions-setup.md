# GitHub Actions CI/CD Setup Guide

## Overview

This guide provides step-by-step instructions for configuring GitHub Actions CI/CD pipeline for OVERLORD v8.1 Trading System.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitHub Environments Setup](#github-environments-setup)
3. [Repository Secrets Configuration](#repository-secrets-configuration)
4. [Branch Protection Rules](#branch-protection-rules)
5. [Initial Deployment Verification](#initial-deployment-verification)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Prerequisites

Before starting, ensure you have:

- ✅ Admin access to `legion14041981-ui/overlord-trading-system-v8` repository
- ✅ Kubernetes clusters (staging + production) with valid credentials
- ✅ Slack workspace with webhook integration enabled
- ✅ Docker registry credentials (GitHub Container Registry - automatically available)
- ✅ SonarCloud and Codecov accounts (optional, for code quality)

---

## GitHub Environments Setup

### 1. Navigate to Repository Settings

```
GitHub Repository → Settings → Environments → New environment
```

### 2. Create Staging Environment

**Name**: `staging`

**Configuration**:
- ⚪ **No protection rules** (auto-deploy on `develop` branch)
- Deployment branches: `develop` only
- No required reviewers
- No wait timer

**Environment Secrets** (staging-specific):
```yaml
KUBECONFIG_STAGING: <base64-encoded kubeconfig>
```

### 3. Create Production Environment

**Name**: `production`

**Configuration**:
- ✅ **Required reviewers**: Add DevOps team members (minimum 1)
- ✅ **Wait timer**: 0 minutes (immediate after approval)
- ✅ **Deployment branches**: `main` only
- ✅ **Prevent self-review**: Enabled

**Environment Secrets** (production-specific):
```yaml
KUBECONFIG_PRODUCTION: <base64-encoded kubeconfig>
```

**Protection Rules**:
```yaml
Required reviewers:
  - @legion14041981-ui  # Add your GitHub username
  - @devops-team-lead   # Add DevOps lead

Deployment branches:
  - main

Wait timer: 0 minutes
Prevent self-review: true
```

---

## Repository Secrets Configuration

### Navigate to Secrets

```
Repository → Settings → Secrets and variables → Actions → New repository secret
```

### Required Secrets

#### 1. **KUBECONFIG_STAGING** (Environment Secret - Staging)

**Description**: Base64-encoded kubeconfig for staging Kubernetes cluster

**Generation**:
```bash
# Option A: From existing kubeconfig
cat ~/.kube/config-staging | base64 -w 0

# Option B: Create service account with limited permissions
kubectl create serviceaccount github-actions -n overlord-staging
kubectl create rolebinding github-actions-deploy \
  --clusterrole=edit \
  --serviceaccount=overlord-staging:github-actions \
  --namespace=overlord-staging

# Get service account token (Kubernetes 1.24+)
kubectl create token github-actions -n overlord-staging --duration=8760h | base64 -w 0
```

**Security**: 
- Use service accounts with **minimum required permissions**
- Limit to specific namespace (`overlord-staging`)
- Rotate every 90 days

---

#### 2. **KUBECONFIG_PRODUCTION** (Environment Secret - Production)

**Description**: Base64-encoded kubeconfig for production Kubernetes cluster

**Generation**: Same as staging, but for production cluster

```bash
kubectl create serviceaccount github-actions -n overlord-production
kubectl create rolebinding github-actions-deploy \
  --clusterrole=edit \
  --serviceaccount=overlord-production:github-actions \
  --namespace=overlord-production

kubectl create token github-actions -n overlord-production --duration=8760h | base64 -w 0
```

**Security**:
- **Never** use cluster-admin role
- Use read-only for non-deployment operations
- Enable audit logging
- Rotate every 30-60 days (production)

---

#### 3. **SLACK_WEBHOOK_URL** (Repository Secret)

**Description**: Slack incoming webhook for deployment notifications

**Setup**:
1. Go to Slack → Your Workspace → Apps → Incoming Webhooks
2. Click "Add to Slack"
3. Select channel (e.g., `#deployments` or `#overlord-alerts`)
4. Copy webhook URL: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`

**Value**:
```
https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Test**:
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚀 GitHub Actions CI/CD setup complete!"}' \
  YOUR_WEBHOOK_URL
```

---

#### 4. **SONAR_TOKEN** (Repository Secret - Optional)

**Description**: SonarCloud authentication token for code quality analysis

**Setup**:
1. Go to [SonarCloud](https://sonarcloud.io/)
2. Create account + link GitHub repository
3. Generate token: Account → Security → Generate Token
4. Copy token

**Value**:
```
squ_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Skip if**: You don't want SonarCloud integration (comment out in workflow)

---

#### 5. **CODECOV_TOKEN** (Repository Secret - Optional)

**Description**: Codecov upload token for test coverage reports

**Setup**:
1. Go to [Codecov.io](https://codecov.io/)
2. Link GitHub repository
3. Copy repository upload token

**Value**:
```
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Skip if**: You don't want Codecov integration (comment out in workflow)

---

#### 6. **GITHUB_TOKEN** (Auto-provided)

**Description**: Automatically provided by GitHub Actions for authentication

**No action required** - GitHub provides this automatically with every workflow run.

**Permissions** (already configured in workflow):
```yaml
permissions:
  contents: read
  packages: write
  security-events: write
```

---

## Branch Protection Rules

Protect critical branches to enforce CI/CD workflow.

### Main Branch Protection

**Navigate**: Repository → Settings → Branches → Add rule

**Branch name pattern**: `main`

**Settings**:
```yaml
✅ Require a pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale pull request approvals when new commits are pushed
  ✅ Require review from Code Owners (if CODEOWNERS file exists)

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  Required checks:
    - quality-gates
    - security-scanning
    - unit-tests
    - integration-tests
    - e2e-tests
    - docker-build

✅ Require conversation resolution before merging

✅ Do not allow bypassing the above settings

❌ Allow force pushes (never allow for main)
❌ Allow deletions
```

### Develop Branch Protection

**Branch name pattern**: `develop`

**Settings**:
```yaml
✅ Require status checks to pass before merging
  Required checks:
    - quality-gates
    - security-scanning
    - unit-tests
    - integration-tests

❌ Require pull request (allow direct commits)
❌ Allow force pushes (with lease)
```

---

## Initial Deployment Verification

### Step 1: Trigger Test Workflow

Create a test branch and trigger the pipeline:

```bash
git checkout -b test/ci-cd-verification
echo "# CI/CD Pipeline Test" >> README.md
git add README.md
git commit -m "test: Verify CI/CD pipeline setup"
git push origin test/ci-cd-verification
```

### Step 2: Monitor Workflow Execution

1. Go to **Actions** tab in GitHub repository
2. Find "CI/CD Full Cycle" workflow
3. Click on the running workflow
4. Monitor each job:
   - ✅ Quality Gates
   - ✅ Security Scanning
   - ✅ Unit Tests
   - ✅ Integration Tests
   - ⏸️ E2E Tests (only on main)
   - ✅ Docker Build

### Step 3: Verify Build Artifacts

Check that Docker image was built and pushed:

```bash
# List images in GitHub Container Registry
gh api /user/packages?package_type=container

# Or visit:
https://github.com/users/legion14041981-ui/packages/container/overlord-trading-system-v8
```

### Step 4: Test Staging Deployment (develop branch)

```bash
git checkout develop
git merge test/ci-cd-verification
git push origin develop
```

**Expected behavior**:
1. Workflow triggers automatically
2. All tests pass
3. Docker image builds
4. **Auto-deploys to staging** (no approval)
5. Smoke tests run
6. Slack notification sent

### Step 5: Test Production Deployment (main branch)

```bash
git checkout main
git merge develop
git push origin main
```

**Expected behavior**:
1. Workflow triggers automatically
2. All tests + E2E tests pass
3. Docker image builds
4. **Waits for approval** (production environment)
5. GitHub sends notification to required reviewers
6. After approval → deploys to production
7. Health checks + smoke tests
8. Slack notification sent

---

## Troubleshooting

### Issue: "No such secret: KUBECONFIG_STAGING"

**Cause**: Secret not configured or wrong environment

**Solution**:
1. Go to Settings → Environments → staging
2. Add `KUBECONFIG_STAGING` as **environment secret** (not repository secret)
3. Ensure workflow uses `environment: staging` for staging deployment

---

### Issue: "Kubernetes authentication failed"

**Cause**: Invalid kubeconfig or expired token

**Solution**:
```bash
# Test kubeconfig locally first
echo $KUBECONFIG_STAGING | base64 -d > /tmp/kubeconfig-test
export KUBECONFIG=/tmp/kubeconfig-test
kubectl get pods -n overlord-staging

# If fails, regenerate token
kubectl create token github-actions -n overlord-staging --duration=8760h
```

---

### Issue: "Docker build failed - rate limit"

**Cause**: Docker Hub rate limiting

**Solution**: Already mitigated in workflow using GitHub Container Registry (ghcr.io)

---

### Issue: "SonarCloud analysis failed"

**Cause**: Missing or invalid SONAR_TOKEN

**Solution**:
- If you don't need SonarCloud, comment out the step in workflow:
```yaml
# - name: SonarCloud Scan
#   uses: SonarSource/sonarcloud-github-action@master
```

---

### Issue: "Slack notification not received"

**Cause**: Invalid webhook URL or wrong channel

**Solution**:
```bash
# Test webhook manually
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from CI/CD"}' \
  $SLACK_WEBHOOK_URL
```

---

### Issue: "Production deployment not triggering"

**Cause**: Environment not configured or wrong branch

**Solution**:
1. Ensure `production` environment exists
2. Check workflow uses `if: github.ref == 'refs/heads/main'`
3. Verify branch protection rules allow pushes to main

---

## Security Best Practices

### Secret Rotation Schedule

| Secret | Rotation Frequency | Priority |
|--------|-------------------|----------|
| `KUBECONFIG_PRODUCTION` | Every 30 days | 🔴 Critical |
| `KUBECONFIG_STAGING` | Every 90 days | 🟡 High |
| `SLACK_WEBHOOK_URL` | On team changes | 🟢 Medium |
| `SONAR_TOKEN` | Every 180 days | 🟢 Low |
| `CODECOV_TOKEN` | Every 180 days | 🟢 Low |

### Audit Checklist

- [ ] All secrets use minimum required permissions
- [ ] Service accounts limited to specific namespaces
- [ ] No cluster-admin roles used
- [ ] Production environment has required reviewers
- [ ] Branch protection enabled for main
- [ ] Slack notifications working
- [ ] Backup kubeconfig stored securely offline
- [ ] Team members trained on approval process
- [ ] Incident response runbook ready
- [ ] Rollback procedure tested

### Emergency Access

In case of GitHub Actions outage:

```bash
# Manual deployment from local machine
export KUBECONFIG=~/.kube/config-production
kubectl set image deployment/overlord \
  overlord=ghcr.io/legion14041981-ui/overlord-trading-system-v8:v1.2.3 \
  -n overlord-production

kubectl rollout status deployment/overlord -n overlord-production
```

---

## Next Steps

After successful setup:

1. ✅ **Test full workflow** on test branch
2. ✅ **Train team** on approval process
3. ✅ **Document** environment-specific configs
4. ✅ **Schedule** first production deployment
5. ✅ **Monitor** initial deployments closely
6. ✅ **Set up** alerts for failed deployments
7. ✅ **Review** logs after first week

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/legion14041981-ui/overlord-trading-system-v8/issues
- Slack: #overlord-devops
- Email: devops@overlord.example.com

---

**Last Updated**: 2026-01-07  
**Version**: 1.0  
**Author**: LEGION v8.1 Autonomous Mission Weaver
