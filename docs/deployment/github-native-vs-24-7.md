# OVERLORD v8.1 — Deployment Architecture Guide

## 🎯 Executive Summary

**Verdict:** `PARTIALLY POSSIBLE` for GitHub-native, `RECOMMENDED` for hybrid approach

OVERLORD Trading System can execute on GitHub Actions in **scheduled batch mode**, but 24/7 continuous runtime requires external hosting with GitHub-managed deployment.

---

## 🔍 Architecture Feasibility Analysis

### 1. GitHub Actions — Scheduled Trading ✅ POSSIBLE

**Status:** IMPLEMENTED  
**Workflow:** `.github/workflows/trading-scheduled.yml`  
**Mode:** Batch processing every 15 minutes

#### Technical Specifications

```yaml
Execution Model: Scheduled cron jobs
Frequency: Every 15 minutes (configurable 5-60 min)
Runtime per cycle: <10 minutes
Total daily executions: ~96 cycles/day
State persistence: External database (PostgreSQL)
Image source: ghcr.io (GHCR)
```

#### GitHub Actions Limits

| Parameter | Limit | Impact |
|-----------|-------|--------|
| Job timeout | 6 hours | Hard kill after 6h |
| Workflow timeout | 72 hours | Multi-job workflows |
| Concurrent jobs | 20-180 | Plan dependent |
| API rate limit | 5000/hour | API interactions |
| Cron minimum | 5 minutes | Fastest execution |
| Cron reliability | Best effort | May delay under load |

**Documentation:** https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration

#### What Works

✅ **Scheduled batch trading** — Execute trades every 15-60 minutes  
✅ **Event-driven execution** — Trigger via webhook/API  
✅ **Manual dispatch** — On-demand execution  
✅ **State management** — Via external database  
✅ **Docker image deployment** — Pull from GHCR  
✅ **Secrets management** — GitHub Secrets  
✅ **Audit trail** — Workflow logs + artifacts  

#### What DOESN'T Work

❌ **24/7 continuous runtime** — Job killed after 6 hours  
❌ **WebSocket connections** — No persistent connections  
❌ **Real-time market streaming** — No sub-second execution  
❌ **Local state persistence** — Ephemeral filesystem  
❌ **Long-running processes** — Must complete within timeout  

#### Technical Reason

> GitHub Actions is designed for **CI/CD automation**, not application hosting.  
> Every job runs in an ephemeral container that is destroyed after completion.

**Hard Limit Location:**  
```
GitHub Actions Runner → Job Timeout Controller
├─ 6 hour maximum runtime per job
├─ Automatic SIGTERM after timeout
└─ No extension mechanism available
```

---

### 2. GitHub Codespaces — ❌ IMPOSSIBLE

**Status:** NOT VIABLE for production

#### Limitations

| Parameter | Value | Reason |
|-----------|-------|--------|
| Idle timeout | 30 minutes | Auto-suspend |
| Max timeout | 4 hours | Hard limit |
| Intended use | Development | Not for production |
| Cost | High | Per-hour compute |
| Reliability | Low | User-facing tool |

**Documentation:** https://docs.github.com/en/codespaces/customizing-your-codespace/setting-your-timeout-period-for-github-codespaces

#### Why It Fails

Codespaces automatically suspends idle processes after 30 minutes and has a maximum runtime of 4 hours. It's designed for **interactive development**, not background services.

---

### 3. GitHub Pages — ❌ IMPOSSIBLE

**Status:** NOT APPLICABLE

#### Architecture

```
GitHub Pages: Static Site Generator
├─ HTML/CSS/JS only
├─ No backend runtime
├─ No database connections
└─ No server-side execution
```

**Documentation:** https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages

---

## 🚀 GitHub-Native Implementation (ACTIVE)

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Schedule: */15 * * * *  (Every 15 minutes)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Pull: ghcr.io/legion14041981-ui/overlord:latest │  │
│  │  2. Execute: Trading Cycle (max 10 min)             │  │
│  │  3. Persist: State → PostgreSQL                      │  │
│  │  4. Upload: Logs → GitHub Artifacts                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Summary → GitHub Actions UI                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │   External Dependencies        │
         ├────────────────────────────────┤
         │ • PostgreSQL (state)           │
         │ • Redis (cache)                │
         │ • Exchange APIs                │
         └────────────────────────────────┘
```

### Execution Flow

1. **Trigger:** Cron schedule fires every 15 minutes
2. **Pre-Flight:** Check market hours and system health
3. **Execution:** Pull Docker image from GHCR and run trading cycle
4. **State Management:** Persist positions and metrics to PostgreSQL
5. **Artifact Upload:** Save execution logs to GitHub
6. **Summary:** Generate step summary in Actions UI

### Required Secrets

```yaml
GitHub Secrets (Repository Settings → Secrets):
  - DATABASE_URL: postgresql://user:pass@host:5432/overlord
  - REDIS_URL: redis://host:6379
  - EXCHANGE_API_KEY: <your-key>
  - EXCHANGE_API_SECRET: <your-secret>
```

### Activation

```bash
# Enable workflow
gh workflow enable trading-scheduled.yml

# Manual trigger for testing
gh workflow run trading-scheduled.yml \
  -f trading_mode=dry-run \
  -f max_positions=3

# View execution logs
gh run list --workflow=trading-scheduled.yml
gh run view <run-id> --log
```

### Monitoring

- **Workflow Runs:** https://github.com/legion14041981-ui/overlord-trading-system-v8/actions
- **Execution Summary:** Available in each run's summary tab
- **Artifacts:** Downloadable logs retained for 30 days

---

## 🏛️ 24/7 Continuous Runtime — Alternative Solutions

### Recommended Architecture: Self-Hosted + GitHub-Managed

**Verdict:** OPTIMAL for production 24/7 trading

```
┌───────────────────────────────────────────────────────────────┐
│                        GitHub                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Source Code Repository                                  │  │
│  │  • CI/CD Pipelines                                       │  │
│  │  • Docker Image Build                                    │  │
│  │  • GHCR Push                                             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                     │
│                          │ (GitHub Actions Deploy)             │
│                          ▼                                     │
└───────────────────────────────────────────────────────────────┘
                           │
                           │ Pull & Deploy
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                Production Environment                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Docker Container (24/7)                                │  │
│  │  • Image: ghcr.io/legion14041981-ui/overlord:latest    │  │
│  │  • Mode: Continuous WebSocket + REST                    │  │
│  │  • State: Persistent volumes                            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  Hosting Options:                                             │
│  1. Self-Hosted Runner (VM/Dedicated Server)                  │
│  2. PaaS (Fly.io / Railway / Render)                          │
│  3. Cloud (AWS ECS / GCP Cloud Run / Azure Container Apps)    │
└───────────────────────────────────────────────────────────────┘
```

### Option 1: Self-Hosted GitHub Actions Runner ⭐ BEST CONTROL

**Architecture:** Dedicated VM with GitHub Actions runner + Docker

#### Advantages

✅ **Full control** over infrastructure  
✅ **No external PaaS costs**  
✅ **Direct GitHub integration**  
✅ **Unlimited runtime** — No 6-hour limit  
✅ **Private network** — Secure trading  
✅ **Cost-effective** — Fixed monthly cost  

#### Setup

```bash
# 1. Provision VM (DigitalOcean, Hetzner, AWS EC2, etc.)
# Recommended: 2 vCPU, 4GB RAM, 50GB SSD

# 2. Install Docker
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER

# 3. Configure self-hosted runner
# GitHub Repo → Settings → Actions → Runners → New self-hosted runner

# 4. Create deployment workflow
cat > .github/workflows/deploy-self-hosted.yml <<EOF
name: Deploy to Self-Hosted

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - name: Pull latest image
        run: |
          docker pull ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest
      
      - name: Restart trading service
        run: |
          docker stop overlord-trading || true
          docker rm overlord-trading || true
          docker run -d \
            --name overlord-trading \
            --restart unless-stopped \
            -e DATABASE_URL="${{ secrets.DATABASE_URL }}" \
            -e REDIS_URL="${{ secrets.REDIS_URL }}" \
            -e EXCHANGE_API_KEY="${{ secrets.EXCHANGE_API_KEY }}" \
            -e EXCHANGE_API_SECRET="${{ secrets.EXCHANGE_API_SECRET }}" \
            ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest
EOF
```

#### Cost Estimate

| Provider | Specs | Monthly Cost |
|----------|-------|-------------|
| DigitalOcean | 2 vCPU, 4GB RAM | $24/month |
| Hetzner | 2 vCPU, 4GB RAM | €4.5/month |
| AWS EC2 t3.medium | 2 vCPU, 4GB RAM | ~$30/month |
| Vultr | 2 vCPU, 4GB RAM | $12/month |

---

### Option 2: PaaS with GitHub Deploy ⭐ EASIEST

**Architecture:** Platform-as-a-Service with GitHub integration

#### Fly.io (Recommended)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Authenticate
fly auth login

# Deploy from GitHub
fly launch --dockerfile Dockerfile --name overlord-trading

# Configure secrets
fly secrets set \
  DATABASE_URL="postgresql://..." \
  REDIS_URL="redis://..." \
  EXCHANGE_API_KEY="..." \
  EXCHANGE_API_SECRET="..."

# Auto-deploy on GitHub push
fly deploy --remote-only
```

**Cost:** Free tier available, ~$5-10/month for production

#### Railway

```bash
# Connect GitHub repository via Railway dashboard
# https://railway.app/new

# Railway automatically:
# 1. Detects Dockerfile
# 2. Builds on every push to main
# 3. Deploys with zero-downtime
# 4. Provides PostgreSQL/Redis add-ons
```

**Cost:** $5/month base + usage

#### Render

```yaml
# render.yaml (auto-detected)
services:
  - type: web
    name: overlord-trading
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
```

**Cost:** Free tier available, $7/month for production

---

### Option 3: Cloud Containers

#### AWS ECS Fargate

```bash
# Deploy via GitHub Actions
cat > .github/workflows/deploy-aws-ecs.yml <<EOF
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: overlord-trading
          cluster: production
EOF
```

**Cost:** ~$30-50/month (Fargate + RDS + ElastiCache)

---

## 📊 Comparison Matrix

| Solution | Cost | Complexity | Control | GitHub Integration | 24/7 Runtime |
|----------|------|------------|---------|-------------------|-------------|
| **GitHub Actions Scheduled** | Free* | Low | Medium | Native | ❌ Batch only |
| **Self-Hosted Runner** | $5-30/mo | Medium | High | Native | ✅ Full |
| **Fly.io** | $5-10/mo | Low | Medium | Via CD | ✅ Full |
| **Railway** | $5-15/mo | Very Low | Medium | Native | ✅ Full |
| **Render** | $7-20/mo | Low | Medium | Native | ✅ Full |
| **AWS ECS** | $30-50/mo | High | High | Via CD | ✅ Full |

*Within GitHub Actions free tier limits

---

## 🎯 Recommended Strategy

### Hybrid Approach: Best of Both Worlds

```
Phase 1: Development & Testing
└─> GitHub Actions Scheduled (FREE)
    • Validate strategies
    • Test execution logic
    • Audit trail in GitHub

Phase 2: Production 24/7
└─> Self-Hosted Runner OR Fly.io
    • Continuous market monitoring
    • Real-time WebSocket feeds
    • Sub-second execution
    • Deployed via GitHub Actions
```

### Deployment Flow

```mermaid
graph LR
    A[Code Push] --> B[GitHub Actions CI]
    B --> C[Build Docker Image]
    C --> D[Push to GHCR]
    D --> E{Deployment Target}
    E -->|Scheduled| F[GitHub Actions Cron]
    E -->|24/7| G[Self-Hosted/PaaS]
    F --> H[Batch Trading]
    G --> I[Continuous Trading]
```

---

## 🛡️ Security Best Practices

### GitHub Secrets Management

```yaml
Required Secrets:
  - DATABASE_URL (encrypted)
  - REDIS_URL (encrypted)
  - EXCHANGE_API_KEY (encrypted)
  - EXCHANGE_API_SECRET (encrypted)

Optional:
  - SLACK_WEBHOOK_URL
  - TELEGRAM_BOT_TOKEN
  - SENTRY_DSN
```

### Network Security

- Use GitHub's IP allowlist for self-hosted runners
- Enable VPN for production deployments
- Restrict database access to runner IP
- Use API key rotation policies

---

## 📝 Conclusion

**For OVERLORD v8.1:**

1. ✅ **GitHub Actions Scheduled** — IMPLEMENTED and ACTIVE
   - Perfect for development, backtesting, and low-frequency trading
   - Zero infrastructure cost
   - Full audit trail

2. ✅ **Self-Hosted + GitHub Deploy** — RECOMMENDED for production
   - 24/7 runtime capability
   - Full control and flexibility
   - GitHub-managed deployment pipeline
   - Cost-effective at scale

3. ✅ **PaaS (Fly.io/Railway)** — ALTERNATIVE for simplicity
   - Easiest setup
   - Minimal maintenance
   - Good for MVP and testing

**Current Status:**  
GitHub-native scheduled trading is **LIVE** and operational.  
24/7 deployment requires external hosting but remains **GitHub-managed** via Actions.

---

## 🔗 References

- [GitHub Actions Limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)
- [GitHub Actions Scheduled Events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)
- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

---

**Last Updated:** 2026-01-09  
**Version:** 8.1.0  
**Status:** Production-Ready
