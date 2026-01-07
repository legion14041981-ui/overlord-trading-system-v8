# CI/CD Setup Checklist - Step by Step

## Overview

This checklist provides **exact commands** to execute for complete CI/CD setup. Follow each step in order.

---

## Prerequisites

### Install Required Tools

```bash
# GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

# kubectl (if not installed)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify installations
gh --version
kubectl version --client
```

---

## Step 1: Authenticate GitHub CLI

```bash
# Login to GitHub
gh auth login

# Select:
# - GitHub.com
# - HTTPS
# - Login with a web browser
# - Follow browser prompts

# Verify authentication
gh auth status

# Expected output:
# ✓ Logged in to github.com as <your-username>
```

**Validation:**
```bash
gh repo view legion14041981-ui/overlord-trading-system-v8
# Should show repository details
```

---

## Step 2: Create GitHub Environments

⚠️ **This must be done via GitHub Web UI** (GitHub CLI doesn't support environment creation)

### Staging Environment

1. Navigate to: https://github.com/legion14041981-ui/overlord-trading-system-v8/settings/environments
2. Click **"New environment"**
3. Name: `staging`
4. **Do NOT** enable protection rules
5. **Do NOT** add required reviewers
6. Deployment branches: Select **"Selected branches"** → Add pattern `develop`
7. Click **"Save protection rules"**

### Production Environment

1. Navigate to: https://github.com/legion14041981-ui/overlord-trading-system-v8/settings/environments
2. Click **"New environment"**
3. Name: `production`
4. ✅ **Enable "Required reviewers"**
   - Add your GitHub username: `legion14041981-ui`
   - Add any other DevOps team members
5. ✅ **Enable "Prevent self-review"**
6. Deployment branches: Select **"Selected branches"** → Add pattern `main`
7. Wait timer: `0` minutes
8. Click **"Save protection rules"**

**Validation:**
- Visit https://github.com/legion14041981-ui/overlord-trading-system-v8/settings/environments
- You should see both `staging` and `production` environments listed

---

## Step 3: Setup Kubernetes Clusters

### Create Namespaces

```bash
# Create staging namespace
kubectl create namespace overlord-staging

# Create production namespace
kubectl create namespace overlord-production

# Verify
kubectl get namespaces | grep overlord
```

### Create Service Accounts

```bash
# Staging service account
kubectl create serviceaccount github-actions -n overlord-staging

# Staging role binding
kubectl create rolebinding github-actions-deploy \
  --clusterrole=edit \
  --serviceaccount=overlord-staging:github-actions \
  --namespace=overlord-staging

# Production service account
kubectl create serviceaccount github-actions -n overlord-production

# Production role binding
kubectl create rolebinding github-actions-deploy \
  --clusterrole=edit \
  --serviceaccount=overlord-production:github-actions \
  --namespace=overlord-production

# Verify
kubectl get serviceaccount -n overlord-staging
kubectl get serviceaccount -n overlord-production
```

### Generate Service Account Tokens

```bash
# Generate staging token (valid for 1 year)
kubectl create token github-actions \
  -n overlord-staging \
  --duration=8760h \
  > /tmp/staging-token.txt

# Generate production token (valid for 1 year)
kubectl create token github-actions \
  -n overlord-production \
  --duration=8760h \
  > /tmp/production-token.txt

# Verify tokens generated
ls -lh /tmp/*-token.txt
```

### Create Kubeconfig Files

```bash
# Get cluster info
KUBE_CLUSTER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
KUBE_CA=$(kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')

# Create staging kubeconfig
cat > /tmp/kubeconfig-staging.yaml <<EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: ${KUBE_CA}
    server: ${KUBE_CLUSTER}
  name: overlord-cluster
contexts:
- context:
    cluster: overlord-cluster
    namespace: overlord-staging
    user: github-actions
  name: overlord-staging
current-context: overlord-staging
users:
- name: github-actions
  user:
    token: $(cat /tmp/staging-token.txt)
EOF

# Create production kubeconfig
cat > /tmp/kubeconfig-production.yaml <<EOF
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: ${KUBE_CA}
    server: ${KUBE_CLUSTER}
  name: overlord-cluster
contexts:
- context:
    cluster: overlord-cluster
    namespace: overlord-production
    user: github-actions
  name: overlord-production
current-context: overlord-production
users:
- name: github-actions
  user:
    token: $(cat /tmp/production-token.txt)
EOF

# Base64 encode for GitHub secrets
cat /tmp/kubeconfig-staging.yaml | base64 -w 0 > /tmp/kubeconfig-staging.b64
cat /tmp/kubeconfig-production.yaml | base64 -w 0 > /tmp/kubeconfig-production.b64

echo "Kubeconfig files generated:"
ls -lh /tmp/kubeconfig-*.b64
```

**Test Kubeconfig:**

```bash
# Test staging kubeconfig
export KUBECONFIG=/tmp/kubeconfig-staging.yaml
kubectl get pods -n overlord-staging

# Test production kubeconfig
export KUBECONFIG=/tmp/kubeconfig-production.yaml
kubectl get pods -n overlord-production

# Restore original kubeconfig
unset KUBECONFIG
```

---

## Step 4: Add GitHub Secrets

### Add Environment Secrets (via Web UI)

⚠️ **Environment secrets cannot be added via CLI** - must use web interface

#### Staging Environment Secret

1. Navigate to: https://github.com/legion14041981-ui/overlord-trading-system-v8/settings/environments
2. Click on **"staging"** environment
3. Click **"Add secret"**
4. Secret name: `KUBECONFIG_STAGING`
5. Secret value: Copy content from `/tmp/kubeconfig-staging.b64`
   ```bash
   cat /tmp/kubeconfig-staging.b64
   ```
6. Click **"Add secret"**

#### Production Environment Secret

1. Click on **"production"** environment
2. Click **"Add secret"**
3. Secret name: `KUBECONFIG_PRODUCTION`
4. Secret value: Copy content from `/tmp/kubeconfig-production.b64`
   ```bash
   cat /tmp/kubeconfig-production.b64
   ```
5. Click **"Add secret"**

### Add Repository Secrets (via CLI)

#### Slack Webhook

```bash
# Get your Slack webhook URL from:
# https://api.slack.com/messaging/webhooks

# Add as repository secret
gh secret set SLACK_WEBHOOK_URL --repo legion14041981-ui/overlord-trading-system-v8
# Paste your webhook URL when prompted

# Verify
gh secret list --repo legion14041981-ui/overlord-trading-system-v8
```

**Test Slack Webhook:**

```bash
SLACK_WEBHOOK_URL="your-webhook-url-here"

curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚀 CI/CD setup test from OVERLORD v8.1"}' \
  "$SLACK_WEBHOOK_URL"

# Expected: "ok" response
# Check your Slack channel for the message
```

#### Optional: SonarCloud (if using)

```bash
# Get token from: https://sonarcloud.io/account/security
gh secret set SONAR_TOKEN --repo legion14041981-ui/overlord-trading-system-v8
```

#### Optional: Codecov (if using)

```bash
# Get token from: https://codecov.io/gh/legion14041981-ui/overlord-trading-system-v8/settings
gh secret set CODECOV_TOKEN --repo legion14041981-ui/overlord-trading-system-v8
```

**Validation:**

```bash
# List all repository secrets
gh secret list --repo legion14041981-ui/overlord-trading-system-v8

# Expected output:
SLACK_WEBHOOK_URL  Updated YYYY-MM-DD
SONAR_TOKEN        Updated YYYY-MM-DD (if added)
CODECOV_TOKEN      Updated YYYY-MM-DD (if added)
```

---

## Step 5: Configure Branch Protection

### Protect Main Branch

```bash
# Enable branch protection (requires admin access)
gh api -X PUT "/repos/legion14041981-ui/overlord-trading-system-v8/branches/main/protection" \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "quality-gates",
      "security-scanning",
      "unit-tests",
      "integration-tests",
      "e2e-tests",
      "docker-build"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {},
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

**If CLI command fails** (common for personal repos), use web UI:

1. Navigate to: https://github.com/legion14041981-ui/overlord-trading-system-v8/settings/branches
2. Click **"Add branch protection rule"**
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require approvals: **1**
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - Add status checks: `quality-gates`, `security-scanning`, `unit-tests`, `integration-tests`, `e2e-tests`, `docker-build`
   - ✅ Require conversation resolution before merging
   - ❌ Do not allow bypassing the above settings
5. Disable:
   - ❌ Allow force pushes
   - ❌ Allow deletions
6. Click **"Create"**

**Validation:**

```bash
# Check branch protection
gh api "/repos/legion14041981-ui/overlord-trading-system-v8/branches/main/protection" | jq '.required_status_checks'
```

---

## Step 6: Test CI/CD Pipeline

### Create Test Branch

```bash
cd /path/to/overlord-trading-system-v8

# Create test branch
git checkout -b test/ci-cd-verification

# Make trivial change
echo "" >> README.md
echo "## CI/CD Pipeline Verified - $(date)" >> README.md

git add README.md
git commit -m "test: Verify CI/CD pipeline setup"

# Push test branch
git push origin test/ci-cd-verification
```

### Monitor Workflow

```bash
# Open Actions page in browser
gh workflow view

# Or visit directly:
echo "Monitor at: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions"

# Watch workflow run (requires gh CLI with run-watch extension)
gh run watch
```

**Expected Results:**

1. Workflow triggers automatically
2. All jobs run:
   - ✅ Quality Gates
   - ✅ Security Scanning
   - ✅ Unit Tests
   - ✅ Integration Tests
   - ✅ Docker Build
   - ⏸️ E2E Tests (skipped - not main branch)
   - ⏸️ Deploy (skipped - not develop/main branch)
3. Docker image pushed to `ghcr.io/legion14041981-ui/overlord-trading-system-v8`

### Test Staging Deployment

```bash
# Merge to develop for staging deployment
git checkout develop
git merge test/ci-cd-verification
git push origin develop
```

**Expected Behavior:**

1. Workflow triggers on `develop` push
2. All tests pass
3. Docker image builds
4. **Auto-deploys to staging** (no approval needed)
5. Smoke tests run
6. Slack notification received

**Verify Staging Deployment:**

```bash
export KUBECONFIG=/tmp/kubeconfig-staging.yaml
kubectl get pods -n overlord-staging
kubectl get svc -n overlord-staging

# Check pod logs
kubectl logs -l app=overlord -n overlord-staging --tail=50
```

### Test Production Deployment

```bash
# Merge to main for production deployment
git checkout main
git merge develop
git push origin main
```

**Expected Behavior:**

1. Workflow triggers on `main` push
2. All tests **+ E2E tests** pass
3. Docker image builds
4. **Waits for approval** (production environment protection)
5. GitHub sends notification to required reviewers
6. You must **manually approve** in Actions UI
7. After approval → deploys to production
8. Health checks + smoke tests run
9. Slack notification received

**Approve Deployment:**

1. Go to: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions
2. Click on the running workflow
3. Click **"Review deployments"**
4. Select `production` environment
5. Click **"Approve and deploy"**

**Verify Production Deployment:**

```bash
export KUBECONFIG=/tmp/kubeconfig-production.yaml
kubectl get pods -n overlord-production
kubectl get svc -n overlord-production

# Check pod logs
kubectl logs -l app=overlord -n overlord-production --tail=50
```

---

## Step 7: Cleanup Test Resources

```bash
# Delete test branch (local)
git branch -D test/ci-cd-verification

# Delete test branch (remote)
git push origin --delete test/ci-cd-verification

# Clean up temporary files
rm -f /tmp/staging-token.txt /tmp/production-token.txt
rm -f /tmp/kubeconfig-*.yaml /tmp/kubeconfig-*.b64

# IMPORTANT: Keep these files backed up securely offline!
# You'll need them for secret rotation.
```

---

## Step 8: Final Validation

Run automated validation script:

```bash
# Run full validation
./scripts/setup-ci-cd.sh --dry-run

# Validate secrets only
./scripts/validate-secrets.sh
```

**Expected Output:**

```
✓ All validation checks passed!
✓ CI/CD setup is ready for production! 🚀
```

---

## Troubleshooting

### Issue: "gh: command not found"

```bash
# Install GitHub CLI (see Prerequisites section)
```

### Issue: "kubectl: command not found"

```bash
# Install kubectl (see Prerequisites section)
```

### Issue: "Cannot access repository"

```bash
# Re-authenticate
gh auth logout
gh auth login

# Verify access
gh repo view legion14041981-ui/overlord-trading-system-v8
```

### Issue: "Service account token expired"

```bash
# Regenerate token (max 1 year duration in Kubernetes)
kubectl create token github-actions -n overlord-staging --duration=8760h

# Update GitHub secret with new token
```

### Issue: "Workflow not triggering"

```bash
# Check workflow file syntax
gh workflow view ci-cd-full-cycle.yml

# Manually trigger workflow
gh workflow run ci-cd-full-cycle.yml --ref main
```

---

## Security Checklist

- [ ] All secrets added to GitHub (not stored locally)
- [ ] Kubeconfig tokens use service accounts (not admin)
- [ ] Service accounts limited to `edit` role (not `cluster-admin`)
- [ ] Production environment has required reviewers
- [ ] Branch protection enabled on `main`
- [ ] Temporary kubeconfig files deleted from `/tmp`
- [ ] Backup kubeconfig stored securely offline
- [ ] Slack webhook tested and working
- [ ] Secret rotation schedule set (30-90 days)
- [ ] Team members trained on approval process

---

## Next Steps

1. ✅ **Monitor first production deployment** closely
2. ✅ **Document any environment-specific configurations**
3. ✅ **Schedule first secret rotation** (add to calendar)
4. ✅ **Train team** on approval workflow
5. ✅ **Set up monitoring alerts** for failed deployments
6. ✅ **Test rollback procedure** in staging

---

**Setup Complete! 🎉**

Your CI/CD pipeline is now production-ready.
