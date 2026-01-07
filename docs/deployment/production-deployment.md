# Production Deployment Guide

## Overview

This guide outlines the complete procedure for deploying OVERLORD v8.1 Trading System to production environment using the automated CI/CD pipeline.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedure](#deployment-procedure)
3. [Approval Workflow](#approval-workflow)
4. [Post-Deployment Verification](#post-deployment-verification)
5. [Monitoring & Observability](#monitoring--observability)
6. [Rollback Procedures](#rollback-procedures)
7. [Incident Response](#incident-response)
8. [Communication Templates](#communication-templates)

---

## Pre-Deployment Checklist

### 1. Code Quality Gates

```bash
# Run locally before pushing
make lint
make test
make integration-test

# Check coverage
make coverage
# Expected: >85% coverage
```

**Validation Criteria:**
- ✅ All unit tests passing (100%)
- ✅ All integration tests passing (100%)
- ✅ Code coverage ≥ 85%
- ✅ No critical security vulnerabilities
- ✅ No linting errors
- ✅ All type checks passing

### 2. Staging Verification

```bash
# Verify staging deployment
export KUBECONFIG=/path/to/kubeconfig-staging.yaml

kubectl get pods -n overlord-staging
kubectl get svc -n overlord-staging

# Check logs for errors
kubectl logs -l app=overlord -n overlord-staging --tail=100 | grep -i error

# Run smoke tests
./scripts/smoke-tests.sh staging
```

**Validation Criteria:**
- ✅ Staging deployment successful
- ✅ All services healthy
- ✅ Smoke tests passing
- ✅ No critical errors in logs
- ✅ API endpoints responsive
- ✅ Database migrations successful

### 3. Infrastructure Readiness

```bash
# Run pre-deployment checks
./scripts/pre-deployment-checks.sh production
```

**Validation Criteria:**
- ✅ Kubernetes cluster accessible
- ✅ Namespace exists and accessible
- ✅ Service account has required permissions
- ✅ Database connection established
- ✅ Redis connection established
- ✅ Storage volumes available
- ✅ Resource quotas sufficient

### 4. Change Management

**Required Documentation:**
- [ ] Changelog updated with new features/fixes
- [ ] Version tag created (semantic versioning)
- [ ] Release notes prepared
- [ ] Rollback plan documented
- [ ] Team notified of deployment window
- [ ] Stakeholders informed

**Risk Assessment:**
- [ ] Database schema changes reviewed
- [ ] Breaking API changes identified
- [ ] Third-party dependencies updated
- [ ] Performance impact analyzed
- [ ] Security implications reviewed

### 5. Team Readiness

**Required Attendees (for production deployment):**
- ✅ DevOps Engineer (deployment executor)
- ✅ Backend Engineer (code owner)
- ✅ QA Engineer (verification)
- ✅ On-call Engineer (incident response)

**Communication Channels:**
- ✅ Slack #overlord-deployments channel active
- ✅ Slack #overlord-alerts channel monitored
- ✅ Incident response contacts available
- ✅ Emergency escalation path defined

---

## Deployment Procedure

### Step 1: Create Release Branch

```bash
cd /path/to/overlord-trading-system-v8

# Ensure on latest develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v1.2.0

# Bump version
nano pyproject.toml  # Update version = "1.2.0"

# Commit version bump
git add pyproject.toml
git commit -m "chore: Bump version to 1.2.0"

# Push release branch
git push origin release/v1.2.0
```

### Step 2: Create Pull Request to Main

```bash
# Create PR using GitHub CLI
gh pr create \
  --base main \
  --head release/v1.2.0 \
  --title "Release v1.2.0" \
  --body "$(cat <<EOF
## Release v1.2.0

### New Features
- Feature 1 description
- Feature 2 description

### Bug Fixes
- Bug fix 1
- Bug fix 2

### Infrastructure Changes
- Infrastructure change 1

### Deployment Checklist
- [x] Code review completed
- [x] All tests passing
- [x] Staging verified
- [x] Documentation updated
- [x] Rollback plan ready

### Rollback Plan
If deployment fails:
1. Trigger rollback via GitHub Actions
2. Revert to previous version: v1.1.0
3. Verify rollback successful
4. Investigate root cause

EOF
)"

# View PR
gh pr view --web
```

### Step 3: Code Review & Approval

**Review Checklist:**
- [ ] Code changes reviewed by at least 1 engineer
- [ ] Database migrations reviewed
- [ ] Security implications reviewed
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Tests adequate for changes

**Approve PR:**
```bash
# Reviewer approves
gh pr review --approve --body "LGTM! Ready for production."

# Check status
gh pr checks
```

### Step 4: Merge to Main

```bash
# Squash merge to main (preserves clean history)
gh pr merge --squash --delete-branch

# Or via web UI:
# Click "Squash and merge" button
```

**This triggers the production deployment workflow automatically.**

### Step 5: Monitor Workflow Execution

```bash
# Watch workflow run
gh run watch

# Or view in browser
echo "Monitor at: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions"
```

**Expected Workflow Steps:**
1. ✅ Quality Gates (3-4 min)
2. ✅ Security Scanning (2-3 min)
3. ✅ Unit Tests (2-3 min)
4. ✅ Integration Tests (3-4 min)
5. ✅ E2E Tests (5-6 min) - **Only on main**
6. ✅ Docker Build (3-4 min)
7. ⏸️ **Production Deployment** (waiting for approval)

---

## Approval Workflow

### Step 6: Review Deployment Request

**GitHub sends notification to required reviewers:**
- Email notification
- GitHub notification bell

**Navigate to:**
https://github.com/legion14041981-ui/overlord-trading-system-v8/actions

**Find the running workflow:**
- Click on "CI/CD Full Cycle" workflow
- Look for yellow status: "⏸️ Waiting for approval"

### Step 7: Verify Pre-Deployment

**Before approving, verify:**

```bash
# Check workflow logs for all passing tests
gh run view --log

# Verify Docker image was built
gh api /users/legion14041981-ui/packages/container/overlord-trading-system-v8/versions

# Check staging is stable
export KUBECONFIG=/path/to/kubeconfig-staging.yaml
kubectl get pods -n overlord-staging
```

**Approval Checklist:**
- [ ] All tests passed (quality-gates, security, unit, integration, e2e)
- [ ] Docker image built successfully
- [ ] Staging environment stable
- [ ] No critical alerts in monitoring
- [ ] Team ready for deployment
- [ ] Rollback plan reviewed

### Step 8: Approve Production Deployment

**Via GitHub UI:**

1. Go to workflow run page
2. Click **"Review deployments"** button (yellow)
3. Review deployment summary:
   - Environment: `production`
   - Image: `ghcr.io/legion14041981-ui/overlord-trading-system-v8:v1.2.0`
   - Commit: `<commit-sha>`
4. Select **`production`** environment checkbox
5. (Optional) Add approval comment:
   ```
   ✅ Approved for production deployment
   - All tests passing
   - Staging verified
   - Team ready
   - Monitoring active
   ```
6. Click **"Approve and deploy"** button

**Via GitHub CLI (alternative):**

```bash
# Get run ID
RUN_ID=$(gh run list --workflow=ci-cd-full-cycle.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# Approve deployment
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/legion14041981-ui/overlord-trading-system-v8/actions/runs/${RUN_ID}/pending_deployments" \
  -f environment_ids[]='production' \
  -f state='approved' \
  -f comment='Approved via CLI'
```

### Step 9: Monitor Deployment

**Deployment executes automatically after approval:**

1. **Pre-deployment checks** (30 sec)
   - Cluster connectivity
   - Namespace access
   - Database connection
   - Redis connection

2. **Kubernetes rollout** (5-10 min)
   - Update deployment manifest
   - Rolling update strategy (25% max surge)
   - Zero-downtime deployment
   - Wait for pods ready

3. **Health checks** (1-2 min)
   - Liveness probe
   - Readiness probe
   - API endpoint verification

4. **Smoke tests** (2-3 min)
   - 10 critical API endpoints
   - Database connectivity
   - Redis connectivity
   - WebSocket connectivity

5. **Slack notification** (immediate)
   - Deployment success/failure
   - Version deployed
   - Duration

**Watch deployment progress:**

```bash
# Watch workflow
gh run watch

# Or monitor Kubernetes directly
export KUBECONFIG=/path/to/kubeconfig-production.yaml

watch -n 2 "kubectl get pods -n overlord-production"

# Watch rollout status
kubectl rollout status deployment/overlord -n overlord-production
```

---

## Post-Deployment Verification

### Step 10: Verify Deployment Success

#### Check Pods Status

```bash
export KUBECONFIG=/path/to/kubeconfig-production.yaml

# All pods should be Running
kubectl get pods -n overlord-production

# Expected output:
# NAME                       READY   STATUS    RESTARTS   AGE
# overlord-xxxxxxxxx-xxxxx   1/1     Running   0          2m
# overlord-xxxxxxxxx-xxxxx   1/1     Running   0          2m
# overlord-xxxxxxxxx-xxxxx   1/1     Running   0          2m
```

#### Check Service Endpoints

```bash
# Get service external IP
kubectl get svc overlord -n overlord-production

# Test health endpoint
SERVICE_IP=$(kubectl get svc overlord -n overlord-production -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl -f http://${SERVICE_IP}:8000/health

# Expected: {"status":"healthy","version":"1.2.0"}
```

#### Run Smoke Tests

```bash
./scripts/smoke-tests.sh production

# Expected output:
# ✓ All 10 smoke tests passed
```

#### Check Logs for Errors

```bash
# Check last 100 lines for errors
kubectl logs -l app=overlord -n overlord-production --tail=100 | grep -i error

# Should return no critical errors

# Check application startup
kubectl logs -l app=overlord -n overlord-production --tail=50

# Look for:
# "Application started successfully"
# "Database connection established"
# "Redis connection established"
```

#### Verify Database Migrations

```bash
# Check migration status
kubectl exec -it deployment/overlord -n overlord-production -- alembic current

# Expected: latest migration head

# Verify database tables
kubectl exec -it deployment/overlord -n overlord-production -- python -c "
import asyncio
from app.db.session import get_db

async def check():
    async for db in get_db():
        result = await db.execute('SELECT COUNT(*) FROM trades')
        print(f'Trades table accessible: {result.scalar()}')
        
asyncio.run(check())
"
```

#### Test Critical User Flows

**Manual verification:**

1. **Authentication**
   ```bash
   curl -X POST http://${SERVICE_IP}:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test123"}'
   ```

2. **Trading API**
   ```bash
   curl http://${SERVICE_IP}:8000/api/v1/trading/markets
   ```

3. **WebSocket Connection**
   ```bash
   # Install websocat if not available: cargo install websocat
   websocat ws://${SERVICE_IP}:8000/ws/trading
   ```

4. **Admin Dashboard** (if applicable)
   - Open in browser: `http://${SERVICE_IP}:8000/admin`
   - Verify UI loads
   - Check metrics dashboard

---

## Monitoring & Observability

### Real-Time Monitoring

#### Kubernetes Metrics

```bash
# Pod resource usage
kubectl top pods -n overlord-production

# Node resource usage
kubectl top nodes

# Watch events
kubectl get events -n overlord-production --sort-by='.lastTimestamp' --watch
```

#### Application Logs

```bash
# Tail logs from all pods
kubectl logs -f -l app=overlord -n overlord-production --all-containers=true

# Filter for errors
kubectl logs -l app=overlord -n overlord-production | grep -E '(ERROR|CRITICAL|FATAL)'

# Filter for specific component
kubectl logs -l app=overlord,component=api -n overlord-production
```

#### Performance Metrics

**Key Metrics to Monitor (first 30 minutes post-deployment):**

1. **Response Time**
   - P50: < 100ms
   - P95: < 500ms
   - P99: < 1000ms

2. **Error Rate**
   - Target: < 0.1%
   - Alert if > 1%

3. **Request Rate**
   - Baseline: ~1000 req/min
   - Alert if deviation > 50%

4. **CPU Usage**
   - Target: < 70%
   - Alert if > 85%

5. **Memory Usage**
   - Target: < 80%
   - Alert if > 90%

6. **Database Connections**
   - Monitor connection pool
   - Alert if > 80% utilization

**Grafana Dashboards** (if configured):
- System Overview: CPU, Memory, Network
- Application Metrics: Request rate, latency, errors
- Database Metrics: Query performance, connections
- Business Metrics: Active trades, orders, users

### Post-Deployment Monitoring Schedule

| Time | Action | Responsible |
|------|--------|-------------|
| T+0 | Immediate verification | DevOps Engineer |
| T+15min | Check metrics baseline | DevOps Engineer |
| T+30min | Review error logs | Backend Engineer |
| T+1hr | Validate business metrics | Product Owner |
| T+4hr | Performance analysis | QA Engineer |
| T+24hr | Full health check | DevOps Team |
| T+7d | Post-deployment review | All stakeholders |

---

## Rollback Procedures

### When to Rollback

**Immediate rollback triggers:**
- 🔴 Critical errors preventing core functionality
- 🔴 Data corruption detected
- 🔴 Security vulnerability exposed
- 🔴 > 5% error rate sustained for > 5 minutes
- 🔴 Complete service outage

**Consideration for rollback:**
- 🟡 Performance degradation > 50%
- 🟡 Elevated error rates (1-5%)
- 🟡 Unexpected behavior affecting users
- 🟡 Failed post-deployment tests

### Automated Rollback

**The CI/CD pipeline includes automatic rollback on failure:**

```yaml
# Triggered automatically if:
# 1. Health checks fail
# 2. Smoke tests fail
# 3. Post-deployment verification fails
```

**Monitor automatic rollback:**

```bash
gh run watch

# Look for "Rollback" job execution
```

### Manual Rollback

#### Option 1: Via GitHub Actions

```bash
# Trigger rollback workflow
gh workflow run rollback.yml \
  -f environment=production \
  -f target_version=v1.1.0

# Monitor rollback
gh run watch
```

#### Option 2: Via Kubernetes (Emergency)

```bash
export KUBECONFIG=/path/to/kubeconfig-production.yaml

# Rollback to previous revision
kubectl rollout undo deployment/overlord -n overlord-production

# Or rollback to specific revision
kubectl rollout history deployment/overlord -n overlord-production
kubectl rollout undo deployment/overlord --to-revision=2 -n overlord-production

# Monitor rollback
kubectl rollout status deployment/overlord -n overlord-production

# Verify pods
kubectl get pods -n overlord-production
```

#### Option 3: Re-deploy Previous Version

```bash
# Get previous release tag
PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)

echo "Previous version: $PREV_TAG"

# Checkout previous tag
git checkout $PREV_TAG

# Push to main (force)
git push origin $PREV_TAG:main --force

# This triggers automatic deployment of previous version
```

### Post-Rollback Actions

1. **Verify rollback successful**
   ```bash
   ./scripts/smoke-tests.sh production
   kubectl get pods -n overlord-production
   ```

2. **Notify team**
   - Slack: #overlord-deployments
   - Include: version rolled back to, reason, duration

3. **Create incident report**
   - What happened
   - Why rollback was needed
   - Impact assessment
   - Root cause analysis (if known)

4. **Schedule post-mortem**
   - Within 24 hours
   - All stakeholders attend
   - Document lessons learned
   - Create action items

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|----------|
| **P0** | Complete outage | 5 minutes | Service down |
| **P1** | Major degradation | 15 minutes | 50% error rate |
| **P2** | Partial outage | 1 hour | Single feature broken |
| **P3** | Minor issue | 4 hours | UI glitch |

### Incident Response Workflow

#### 1. Detection

**Automated alerts:**
- Slack: #overlord-alerts
- PagerDuty (if configured)
- Email to on-call engineer

**Manual detection:**
- User reports
- Monitoring dashboard
- Log analysis

#### 2. Triage

```bash
# Quick assessment
kubectl get pods -n overlord-production
kubectl logs -l app=overlord -n overlord-production --tail=100
kubectl top pods -n overlord-production

# Check recent deployments
kubectl rollout history deployment/overlord -n overlord-production
```

**Determine severity:**
- Impact: How many users affected?
- Duration: How long has it been happening?
- Trend: Getting worse or stable?

#### 3. Response

**P0/P1 Incidents:**
1. Declare incident in #overlord-incidents
2. Assign incident commander
3. Execute rollback if deployment-related
4. Engage all hands
5. Implement fix or workaround
6. Communicate status every 15 minutes

**P2/P3 Incidents:**
1. Log in incident tracker
2. Assign owner
3. Investigate root cause
4. Implement fix
5. Deploy fix in next release

#### 4. Resolution

```bash
# Verify fix
./scripts/smoke-tests.sh production
kubectl get pods -n overlord-production

# Monitor metrics
watch -n 10 "kubectl top pods -n overlord-production"
```

#### 5. Post-Incident

- [ ] Update incident status
- [ ] Notify stakeholders
- [ ] Document incident timeline
- [ ] Schedule post-mortem (within 48 hours)
- [ ] Create action items from lessons learned

---

## Communication Templates

### Pre-Deployment Announcement

**Slack: #overlord-deployments**

```
🚀 PRODUCTION DEPLOYMENT SCHEDULED

Version: v1.2.0
Scheduled: 2026-01-07 14:00 UTC
Duration: ~30 minutes
Downtime: None (zero-downtime deployment)

Changes:
• Feature: New trading algorithm
• Fix: WebSocket reconnection bug
• Performance: 20% faster order execution

Impact: None expected

Rollback Plan: Automatic rollback to v1.1.0 if health checks fail

Team:
• Deployment: @devops-engineer
• Code Owner: @backend-engineer
• Verification: @qa-engineer
• On-call: @on-call-engineer

Questions? Reply in thread.
```

### Deployment In Progress

**Slack: #overlord-deployments**

```
⏳ DEPLOYMENT IN PROGRESS

Version: v1.2.0
Status: Waiting for approval

Workflow: https://github.com/legion14041981-ui/overlord-trading-system-v8/actions/runs/12345

Pre-deployment checks: ✅ PASSED
• All tests passed
• Docker image built
• Staging verified

Awaiting approval from: @devops-lead
```

### Deployment Success

**Slack: #overlord-deployments**

```
✅ DEPLOYMENT SUCCESSFUL

Version: v1.2.0
Duration: 12 minutes
Completed: 2026-01-07 14:12 UTC

Verification:
• All pods running: 3/3
• Health checks: PASSING
• Smoke tests: PASSING
• Error rate: 0.02% (normal)
• Response time: 95ms p95 (normal)

Monitoring: Active for next 4 hours

Thanks to the team! 🎉
```

### Deployment Failure

**Slack: #overlord-deployments + #overlord-incidents**

```
🚨 DEPLOYMENT FAILED - ROLLBACK INITIATED

Version: v1.2.0 (failed)
Reason: Health checks failed - HTTP 503 errors
Duration: 8 minutes before rollback

Rollback Status: IN PROGRESS
Target: v1.1.0 (previous stable version)

Current Status:
• Service: DEGRADED (attempting rollback)
• Users affected: Estimated 10%
• Incident: P1 declared

Incident Commander: @devops-lead

Next update: 5 minutes

DO NOT deploy anything until rollback completes.
```

### Rollback Success

**Slack: #overlord-incidents**

```
✅ ROLLBACK SUCCESSFUL

Rolled back to: v1.1.0
Duration: 5 minutes
Completed: 2026-01-07 14:25 UTC

Verification:
• Service: HEALTHY
• All pods running: 3/3
• Error rate: 0.01% (back to normal)
• Users affected: Restored

Incident: Closed
Post-mortem: Scheduled for 2026-01-08 10:00 UTC

Root cause: Under investigation

Thanks for quick response! 🛡️
```

---

## Production Deployment Checklist

### Pre-Deployment (T-24 hours)

- [ ] All tests passing in CI/CD
- [ ] Code review completed and approved
- [ ] Staging environment verified
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version tag created
- [ ] Rollback plan documented
- [ ] Team availability confirmed
- [ ] Stakeholders notified
- [ ] Monitoring alerts configured

### Deployment Day (T-0)

- [ ] Pre-deployment checks executed
- [ ] Infrastructure validated
- [ ] Team on standby
- [ ] Communication channels ready
- [ ] PR merged to main
- [ ] Workflow triggered
- [ ] Approval granted
- [ ] Deployment monitoring active

### Post-Deployment (T+0 to T+4 hours)

- [ ] Pods healthy and running
- [ ] Health checks passing
- [ ] Smoke tests passed
- [ ] Logs reviewed (no critical errors)
- [ ] Performance metrics baseline
- [ ] Error rate normal
- [ ] User flows verified
- [ ] Team notified of success
- [ ] Monitoring continues

### Post-Deployment (T+24 hours)

- [ ] Full health check completed
- [ ] Performance analysis done
- [ ] User feedback collected
- [ ] Incident count reviewed
- [ ] Metrics compared to baseline
- [ ] Documentation finalized
- [ ] Lessons learned documented

---

## Metrics & KPIs

### Deployment Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Deployment frequency | Weekly | |
| Lead time (commit to prod) | < 1 hour | |
| Deployment duration | < 15 minutes | |
| Deployment success rate | > 95% | |
| Rollback rate | < 5% | |
| Mean time to recovery (MTTR) | < 30 minutes | |

### Quality Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Test coverage | > 85% | |
| Test pass rate | 100% | |
| Security vulnerabilities (critical) | 0 | |
| Code review approval time | < 4 hours | |
| Linting compliance | 100% | |

### Production Stability

| Metric | Target | Actual |
|--------|--------|--------|
| Uptime (monthly) | > 99.9% | |
| Error rate | < 0.1% | |
| Response time (p95) | < 500ms | |
| Incident count (monthly) | < 5 | |
| P0/P1 incidents | 0 | |

---

## References

- [GitHub Actions Setup Guide](github-actions-setup.md)
- [Setup Checklist](setup-checklist.md)
- [Pre-Deployment Checks Script](../../scripts/pre-deployment-checks.sh)
- [Smoke Tests Script](../../scripts/smoke-tests.sh)
- [CI/CD Workflow](../../.github/workflows/ci-cd-full-cycle.yml)

---

**Last Updated**: 2026-01-07  
**Version**: 1.0  
**Owner**: LEGION v8.1 DevOps Team
