# 🚀 OVERLORD CI/CD — Quick Start Guide

**Deploy from Code to Production in 15 Minutes**

---

## Table of Contents

1. [Automated Setup (Recommended)](#automated-setup-recommended)
2. [Manual Setup](#manual-setup)
3. [First Deployment Test](#first-deployment-test)
4. [Production Deployment Workflow](#production-deployment-workflow)
5. [Monitoring & Verification](#monitoring--verification)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Procedures](#emergency-procedures)

---

## Automated Setup (Recommended)

### Prerequisites

Install required tools:

```bash
# macOS
brew install gh kubectl curl jq

# Ubuntu/Debian
sudo apt-get install gh kubectl curl jq

# Authenticate GitHub CLI
gh auth login
```

### One-Command Setup

```bash
# Clone repository
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Run automated setup wizard
chmod +x scripts/github-setup-automation.sh
./scripts/github-setup-automation.sh

# Or dry-run first (no changes, just shows what would happen)
./scripts/github-setup-automation.sh --dry-run
```

### What the Script Does

The automated setup wizard will:

1. ✅ **Create GitHub Environments**
   - `staging` (auto-deploy from `develop`)
   - `production` (requires approval)

2. ✅ **Configure Kubernetes Credentials**
   - Prompts for staging/production contexts
   - Creates service accounts with minimal permissions
   - Generates time-limited tokens (1 year validity)
   - Stores as environment secrets

3. ✅ **Set Up Slack Notifications**
   - Tests webhook connectivity
   - Configures deployment notifications

4. ✅ **Enable Branch Protection**
   - Protects `main` branch (requires PR + reviews)
   - Protects `develop` branch (requires CI checks)

5. ✅ **Verify Configuration**
   - Checks all environments exist
   - Validates secrets
   - Confirms branch protection

### Interactive Prompts

During setup, you'll be asked:

```
Repository: legion14041981-ui/overlord-trading-system-v8
Mode: LIVE (will make changes)

This will modify your GitHub repository. Continue? (y/N): y

▶️  STEP 1: Creating GitHub Environments

ℹ️  Enter required reviewers for production (comma-separated):
Reviewers (default: legion14041981-ui): legion14041981-ui,devops-lead

▶️  STEP 2: Configuring Kubernetes Credentials

ℹ️  Enter Kubernetes context for STAGING:
  docker-desktop
  minikube
  gke_my-project_us-central1_staging-cluster
  
Context: gke_my-project_us-central1_staging-cluster
Namespace (default: overlord-staging): overlord-staging

▶️  STEP 3: Configuring Slack Notifications

Enter Slack webhook URL (or press Enter to skip): https://hooks.slack.com/services/T.../B.../XXX

▶️  STEP 4: Configuring Optional Secrets

Configure SonarCloud? (y/N): n
Configure Codecov? (y/N): n

▶️  STEP 5: Setting Up Branch Protection Rules

▶️  STEP 6: Verifying Configuration

✅ ✨ Setup completed successfully!

Next steps:
  1. Test workflow: git push origin develop
  2. Monitor: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions
  3. Check Slack notifications
  4. Review deployment logs
```

---

## Manual Setup

If you prefer manual configuration, follow [GitHub Actions Setup Guide](./github-actions-setup.md).

### Quick Manual Steps

1. **Create Environments**
   ```
   Repository → Settings → Environments → New environment
   
   Environment: staging
   - No protection rules
   - Deployment branches: develop only
   
   Environment: production
   - Required reviewers: Add your username
   - Deployment branches: main only
   ```

2. **Add Secrets**
   ```bash
   # Generate Kubernetes credentials
   kubectl create token github-actions -n overlord-staging --duration=8760h | base64
   
   # Add as environment secret:
   Settings → Environments → staging → Add secret
   Name: KUBECONFIG_STAGING
   Value: <base64-encoded-kubeconfig>
   
   # Repeat for production
   ```

3. **Configure Slack**
   ```
   Settings → Secrets → Actions → New repository secret
   Name: SLACK_WEBHOOK_URL
   Value: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

4. **Enable Branch Protection**
   ```
   Settings → Branches → Add rule
   
   Branch: main
   ☑ Require a pull request before merging
   ☑ Require status checks to pass
   ☑ Require conversation resolution
   ```

---

## First Deployment Test

### Test on Staging (develop branch)

```bash
# Create test branch
git checkout -b test/ci-cd-pipeline
echo "CI/CD test" >> README.md
git add README.md
git commit -m "test: Verify CI/CD pipeline"
git push origin test/ci-cd-pipeline

# Merge to develop
git checkout develop
git merge test/ci-cd-pipeline
git push origin develop
```

### Expected Workflow

1. **GitHub Actions triggers automatically**
   - Go to: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions
   - Find "CI/CD Full Cycle" workflow

2. **Pipeline executes 9 jobs** (5-10 minutes)
   ```
   ✅ quality-gates       (2 min)  - Linting, type checking, security
   ✅ security-scanning   (3 min)  - Trivy, Snyk, CodeQL
   ✅ unit-tests          (2 min)  - Python + Node.js tests
   ✅ integration-tests   (3 min)  - API + DB tests
   ⏭️  e2e-tests          (skip)   - Only on main branch
   ✅ docker-build        (4 min)  - Multi-stage build + scan
   ✅ deploy-staging      (2 min)  - Kubernetes deployment
   ✅ post-deploy-checks  (1 min)  - Health + smoke tests
   ✅ notify              (10 sec) - Slack notification
   ```

3. **Slack notification received**
   ```
   🚀 OVERLORD Deployment - STAGING
   Status: ✅ SUCCESS
   Environment: staging
   Branch: develop
   Commit: abc1234 (Test CI/CD)
   Author: legion14041981-ui
   Duration: 8m 32s
   
   View logs: [GitHub Actions]
   ```

4. **Verify staging deployment**
   ```bash
   # Check Kubernetes pods
   kubectl get pods -n overlord-staging
   
   # Check service
   kubectl get svc -n overlord-staging
   
   # Test API
   curl https://staging.overlord.example.com/health
   ```

### Troubleshooting First Deployment

#### ❌ Workflow doesn't trigger
```bash
# Check if workflow file exists
gh api repos/legion14041981-ui/overlord-trading-system-v8/contents/.github/workflows/ci-cd-full-cycle.yml

# Check branch protection
gh api repos/legion14041981-ui/overlord-trading-system-v8/branches/develop/protection
```

#### ❌ Kubernetes deployment fails
```bash
# Check secret is configured
gh secret list --repo legion14041981-ui/overlord-trading-system-v8 --env staging

# Validate kubeconfig locally
echo $KUBECONFIG_STAGING | base64 -d > /tmp/test-kubeconfig
KUBECONFIG=/tmp/test-kubeconfig kubectl get pods
```

#### ❌ Docker build fails
```bash
# Check if Dockerfile exists
gh api repos/legion14041981-ui/overlord-trading-system-v8/contents/Dockerfile

# Test build locally
docker build -t overlord:test .
```

---

## Production Deployment Workflow

### Standard Release Process

```bash
# 1. Ensure staging is stable
kubectl get pods -n overlord-staging
curl https://staging.overlord.example.com/health

# 2. Create release PR
git checkout main
git pull origin main
git merge develop
git push origin main

# Or create PR via GitHub UI:
# Compare: main ← develop
# Title: "Release v1.2.3 - Production deployment"
# Description:
#   - Feature X
#   - Bug fix Y
#   - Performance improvement Z
```

### Approval Gate

1. **GitHub sends notification** to required reviewers
   ```
   📧 Email: "Deployment approval required for production"
   
   Environment: production
   Workflow: CI/CD Full Cycle
   Commit: abc1234
   Author: legion14041981-ui
   ```

2. **Reviewer approves deployment**
   ```
   Actions → Workflow run → "Review deployments"
   
   ☑ production
   Comment: "LGTM, all staging tests passed"
   [Approve and deploy]
   ```

3. **Deployment proceeds automatically**
   ```
   ✅ All checks passed
   ⏸️  Waiting for approval...
   ✅ Approved by @legion14041981-ui
   🚀 Deploying to production...
   ✅ Health checks passed
   ✅ Smoke tests passed
   ✅ Deployment complete
   ```

### Post-Deployment Verification

```bash
# 1. Check Kubernetes status
kubectl get pods -n overlord-production
kubectl rollout status deployment/overlord -n overlord-production

# 2. Verify services
kubectl get svc,ingress -n overlord-production

# 3. Test API health
curl https://api.overlord.example.com/health
curl https://api.overlord.example.com/metrics

# 4. Check logs
kubectl logs -f deployment/overlord -n overlord-production

# 5. Monitor metrics
# Open Grafana: https://grafana.example.com/d/overlord
# Check:
#   - Request rate
#   - Error rate (<1%)
#   - Response time (<200ms p95)
#   - Pod CPU/Memory
```

### Rollback (if needed)

```bash
# Option 1: Kubernetes rollback (immediate)
kubectl rollout undo deployment/overlord -n overlord-production

# Option 2: Redeploy previous version
git revert HEAD
git push origin main
# Wait for approval → auto-deploys

# Option 3: Manual rollback
kubectl set image deployment/overlord \
  overlord=ghcr.io/legion14041981-ui/overlord-trading-system-v8:v1.2.2 \
  -n overlord-production
```

---

## Monitoring & Verification

### Real-Time Monitoring

```bash
# Watch workflow status
gh run watch

# Stream logs from specific job
gh run view --log --job docker-build

# Check latest runs
gh run list --limit 10
```

### Deployment Health Dashboard

Create a monitoring dashboard:

```yaml
# config/monitoring/deployment-dashboard.yaml
datasources:
  - name: GitHub Actions
    type: github
    url: https://api.github.com
    
panels:
  - title: "Deployment Success Rate"
    query: |
      SELECT 
        date_trunc('day', created_at) as date,
        COUNT(*) FILTER (WHERE conclusion = 'success') * 100.0 / COUNT(*) as success_rate
      FROM workflow_runs
      WHERE name = 'CI/CD Full Cycle'
      GROUP BY date
      ORDER BY date DESC
      LIMIT 30
      
  - title: "Average Deployment Duration"
    query: |
      SELECT 
        environment,
        AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) / 60 as avg_minutes
      FROM deployments
      WHERE status = 'success'
      GROUP BY environment
      
  - title: "Deployment Frequency"
    query: |
      SELECT 
        date_trunc('week', created_at) as week,
        environment,
        COUNT(*) as deployments
      FROM deployments
      GROUP BY week, environment
      ORDER BY week DESC
```

### Slack Alerts Configuration

Customize Slack notifications:

```yaml
# .github/workflows/notify-config.yml
slack:
  channels:
    success: '#deployments'
    failure: '#incidents'
  
  mentions:
    production:
      success: '@channel'
      failure: '@devops-oncall <!here>'
    staging:
      success: ''
      failure: '@devops'
  
  templates:
    success: |
      🚀 *OVERLORD Deployment - {environment}*
      Status: ✅ *SUCCESS*
      Branch: `{branch}`
      Commit: `{commit}` ({commit_message})
      Author: {author}
      Duration: {duration}
      
      <{run_url}|View logs> | <{deployment_url}|Open service>
      
    failure: |
      🚨 *OVERLORD Deployment FAILED - {environment}*
      Status: ❌ *FAILURE*
      Branch: `{branch}`
      Commit: `{commit}`
      Author: {author}
      Failed job: {failed_job}
      Error: {error_message}
      
      <{run_url}|View logs> | <{docs_url}|Troubleshooting>
      
      {mentions}
```

---

## Troubleshooting

### Common Issues

#### 1. "Environment not found: staging"

**Cause**: Environment not created or wrong name

**Solution**:
```bash
# List environments
gh api repos/legion14041981-ui/overlord-trading-system-v8/environments

# Create environment
gh api -X PUT repos/legion14041981-ui/overlord-trading-system-v8/environments/staging
```

#### 2. "Kubernetes authentication failed"

**Cause**: Invalid or expired kubeconfig

**Solution**:
```bash
# Test kubeconfig locally
echo $KUBECONFIG_STAGING | base64 -d > /tmp/test-config
KUBECONFIG=/tmp/test-config kubectl get pods

# If fails, regenerate token
kubectl create token github-actions -n overlord-staging --duration=8760h

# Update secret
echo "<new-kubeconfig>" | gh secret set KUBECONFIG_STAGING --env staging
```

#### 3. "No required reviewers for production"

**Cause**: Production environment not configured with reviewers

**Solution**:
```
1. Go to: Settings → Environments → production
2. Under "Deployment protection rules"
3. Click "Required reviewers"
4. Add usernames: legion14041981-ui, devops-lead
5. Save
```

#### 4. "Docker image push failed"

**Cause**: Insufficient permissions or registry not configured

**Solution**:
```bash
# Check GITHUB_TOKEN permissions in workflow
permissions:
  packages: write  # ← Must be present
  
# Verify registry access
gh auth token | docker login ghcr.io -u legion14041981-ui --password-stdin
```

#### 5. "Smoke tests failed"

**Cause**: Service not responding after deployment

**Solution**:
```bash
# Check pod status
kubectl get pods -n overlord-staging
kubectl describe pod <pod-name> -n overlord-staging

# Check service
kubectl get svc -n overlord-staging

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://overlord.overlord-staging.svc.cluster.local/health
```

---

## Emergency Procedures

### Emergency Rollback (Production)

```bash
# IMMEDIATE ROLLBACK (< 1 minute)
kubectl rollout undo deployment/overlord -n overlord-production

# Verify rollback
kubectl rollout status deployment/overlord -n overlord-production

# Check service health
curl https://api.overlord.example.com/health

# Notify team
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🚨 EMERGENCY ROLLBACK executed on production"}' \
  $SLACK_WEBHOOK_URL
```

### Disable Auto-Deployment

```bash
# Temporarily disable workflow
gh workflow disable "CI/CD Full Cycle"

# Or edit workflow file
# Add to .github/workflows/ci-cd-full-cycle.yml:
on:
  workflow_dispatch:  # Manual trigger only
  # push:  # ← Comment out auto-trigger
```

### Incident Response Checklist

- [ ] 1. **Stop the bleeding** - Rollback if necessary
- [ ] 2. **Assess impact** - Check error rates, user reports
- [ ] 3. **Notify stakeholders** - Slack, email, status page
- [ ] 4. **Investigate root cause** - Logs, metrics, traces
- [ ] 5. **Document incident** - Timeline, actions, resolution
- [ ] 6. **Create fix** - PR with solution
- [ ] 7. **Test fix** - Staging deployment
- [ ] 8. **Deploy fix** - Production with approval
- [ ] 9. **Verify resolution** - Monitoring, smoke tests
- [ ] 10. **Post-mortem** - Review, improve, prevent

---

## Additional Resources

- **Full Setup Guide**: [github-actions-setup.md](./github-actions-setup.md)
- **Setup Checklist**: [setup-checklist.md](./setup-checklist.md)
- **Production Deployment SOP**: [production-deployment.md](./production-deployment.md)
- **Secrets Template**: [secrets-template.env](./secrets-template.env)

---

**Last Updated**: 2026-01-07  
**Version**: 1.0  
**Maintainer**: LEGION v8.1 Autonomous Mission Weaver
