# 🚀 Overlord v8.1 - Autonomous Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.28+-326CE5.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/docker-20.10+-2496ED.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Grail Agent](https://img.shields.io/badge/security-Grail%20Agent-green.svg)]()
[![CI/CD](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions/workflows/ci-cd-full-cycle.yml/badge.svg)](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)
[![Deployment](https://img.shields.io/badge/deployment-automated-success.svg)](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)

> Enterprise-grade autonomous trading system with multi-exchange integration, real-time risk management, and production-ready Kubernetes infrastructure.
>
> **NEW in v8.1**: Integrated with **Grail Agent** security layer, **Overlord Bootstrap** initialization system, and **Full CI/CD Pipeline**

## 📝 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Grail Agent & Overlord Bootstrap](#grail-agent--overlord-bootstrap)
- [🚀 CI/CD Pipeline](#-cicd-pipeline) **← NEW**
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

**Overlord v8.1** is a production-ready autonomous trading system designed for high-frequency trading across multiple cryptocurrency exchanges. Built with enterprise-grade reliability, scalability, and security in mind.

### Key Capabilities

- ⚡ **High Performance**: Sub-millisecond order execution
- 🔄 **Multi-Exchange**: Walbi, Binance, and extensible architecture
- 🛡️ **Risk Management**: Real-time position monitoring and automated safeguards
- 📊 **Monitoring**: Comprehensive metrics with Prometheus & Grafana
- 🚀 **Production Ready**: Kubernetes-native with auto-scaling
- 🔐 **Secure**: Grail Agent security layer with token validation
- ⚙️ **Modular**: Overlord Bootstrap for clean initialization
- 🔄 **CI/CD**: Automated testing, building, and deployment pipeline

## ✨ Features

### Trading Engine

- **Real-time Market Data**: WebSocket connections for live pricing
- **Order Management**: Support for market, limit, and advanced order types
- **Position Tracking**: Real-time P&L calculations
- **Strategy Engine**: Pluggable strategy framework

### Risk Management

- **Position Limits**: Per-asset and portfolio-level limits
- **Stop-Loss**: Automated stop-loss execution
- **Circuit Breakers**: Emergency trading halt mechanisms
- **Exposure Monitoring**: Real-time risk metrics

### Security (Grail Agent)

- **Token Validation**: GitHub PAT and session token validation
- **Multi-level Auth**: JWT, OAuth, API keys support
- **Blacklist Management**: Real-time token revocation
- **Audit Logging**: Complete security event tracking

### Infrastructure

- **Kubernetes**: Native K8s deployment with HPA
- **Database**: PostgreSQL with automated backups
- **Caching**: Redis for session state and rate limiting
- **Monitoring**: Prometheus, Grafana, AlertManager

### DevOps

- **CI/CD**: GitHub Actions with automated testing
- **IaC**: Terraform for infrastructure provisioning
- **Security**: Trivy and Snyk scanning
- **Deployment**: Helm charts with multi-environment support

## 🏝️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Walbi   │  │ Binance  │  │  Other   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└────────┴─────────────┴─────────────┴─────────────────────────┘
        │             │             │
        └─────────────┴───────────────┘
                      │
        ┌─────────────┴───────────────┐
        │    NGINX Ingress          │
        │  (SSL/TLS Termination)    │
        └─────────────┬───────────────┘
                      │
        ┌─────────────┴───────────────┐
        │   Overlord Trading API    │
        │  ┌──────────────────────┐ │
        │  │ Overlord Bootstrap  │ │  ← Initialization system
        │  │ Grail Agent Security│ │  ← Token validation
        │  │ Trading Engine      │ │  ← Order execution
        │  │ Risk Management     │ │  ← Risk controls
        │  └──────────────────────┘ │
        └─────┬──────────────┬──────┘
              │              │
    ┌─────────┴────┐  ┌──────┴──────┐
    │ PostgreSQL   │  │    Redis    │
    │  (RDS)       │  │ (ElastiCache)│
    └──────────────┘  └─────────────┘
              │
    ┌─────────┴─────────────┐
    │  Prometheus Metrics   │
    └─────────┬─────────────┘
              │
    ┌─────────┴─────────────┐
    │   Grafana Dashboards  │
    └─────────────────────────┘
```

## 🔐 Grail Agent & Overlord Bootstrap

### Grail Agent (Security Layer)

Grail Agent - это продвинутая система безопасности и валидации токенов:

**Основные возможности:**
- ✅ Валидация GitHub PAT токенов
- ✅ Генерация session токенов с HMAC-подписью
- ✅ Управление blacklist (чёрный список токенов)
- ✅ Проверка разрешений
- ✅ Аудит и логирование

**Пример использования:**
```python
from src.auth import get_grail_agent

# Получить singleton instance
grail = get_grail_agent()

# Валидация GitHub токена
is_valid, metadata = grail.validate_github_token(token)

# Генерация session токена
session_token = grail.generate_session_token("user_id", ttl_seconds=3600)

# Проверка session токена
is_valid, user_id = grail.verify_session_token(session_token)
```

### Overlord Bootstrap (Initialization System)

Overlord Bootstrap - это главный инициализатор системы:

**Режимы работы:**
- `dry-run` - Эмуляция без реального выполнения
- `conservative` - Безопасный режим (по умолчанию)
- `standard` - Стандартный режим
- `aggressive` - Максимальная автоматизация

**Пример использования:**
```python
from src.core.bootstrap import create_overlord

# Создать Overlord
overlord = create_overlord(
    config_path="config/default.yaml",
    mode="standard"
)

# Запустить
if overlord.start():
    # Проверка здоровья
    health = overlord.health_check()
    print(f"Status: {health['status']}")
    
    # Система работает...
    
    # Остановка
    overlord.stop()
```

---

## 🚀 CI/CD Pipeline

### Overview

Full-cycle automated CI/CD pipeline with:
- ✅ **9-stage pipeline**: Quality → Security → Testing → Build → Deploy
- ✅ **Multi-environment**: Staging (auto) + Production (approval gate)
- ✅ **Zero-downtime deployments**: Rolling updates with health checks
- ✅ **Automatic rollback**: On health/smoke test failures
- ✅ **Slack notifications**: Real-time deployment status

### Quick Setup

```bash
# One-command automated setup
./scripts/github-setup-automation.sh

# Or dry-run first (no changes)
./scripts/github-setup-automation.sh --dry-run
```

### Pipeline Stages

```mermaid
graph LR
    A[Quality Gates] --> B[Security Scanning]
    B --> C[Unit Tests]
    C --> D[Integration Tests]
    D --> E[E2E Tests]
    E --> F[Docker Build]
    F --> G[Deploy Staging]
    G --> H[Health Checks]
    H --> I[🚀 Production Approval]
    I --> J[Deploy Production]
    J --> K[Post-Deploy Verification]
```

### Deployment Workflow

**Staging (Auto-deploy on `develop` branch)**:
```bash
git push origin develop
# → Auto-triggers pipeline
# → Deploys to staging
# → Slack notification
```

**Production (Requires approval on `main` branch)**:
```bash
git push origin main
# → Pipeline runs all tests
# → Waits for approval
# → Reviewer approves in GitHub Actions
# → Deploys to production
# → Slack notification
```

### Documentation

- **[🚀 Quick Start Guide](docs/deployment/QUICK_START_CI_CD.md)** - Setup in 15 minutes
- **[Setup Guide](docs/deployment/github-actions-setup.md)** - Detailed configuration
- **[Setup Checklist](docs/deployment/setup-checklist.md)** - Interactive checklist
- **[Production Deployment](docs/deployment/production-deployment.md)** - SOP for production
- **[Secrets Template](docs/deployment/secrets-template.env)** - Security best practices

### Monitoring

```bash
# Watch workflow in real-time
gh run watch

# View latest runs
gh run list --limit 10

# Check deployment status
kubectl rollout status deployment/overlord -n overlord-production
```

---

## 📦 Prerequisites

### Local Development

- Python 3.11+
- Docker 20.10+
- kubectl 1.28+
- Helm 3.12+
- Terraform 1.5+

### Cloud Infrastructure

- AWS Account with appropriate permissions
- EKS cluster (or ability to create one)
- RDS PostgreSQL instance
- ElastiCache Redis cluster

### CI/CD Setup

- GitHub repository admin access
- Kubernetes cluster credentials (staging + production)
- Slack webhook (optional, for notifications)
- GitHub CLI (`gh`) installed

## 🚀 Quick Start

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy config template
cp config/default.yaml config/local.yaml

# Start Overlord in dry-run mode
export OVERLORD_CONFIG=config/local.yaml
export OVERLORD_MODE=dry-run
python src/main.py
```

### Docker Compose (Recommended for Local Dev)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f overlord

# Access API
curl http://localhost:8000/health

# Stop services
docker-compose down
```

### Testing Grail Agent

```bash
# Run Grail Agent tests
python -m pytest tests/auth/test_grail_agent.py -v

# Test token validation via API
curl -X GET http://localhost:8000/api/v1/grail/token/validate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## ⚙️ Configuration

### Environment Variables

```bash
# Overlord Core
export OVERLORD_MODE=standard                    # dry-run, conservative, standard, aggressive
export OVERLORD_CONFIG=config/production.yaml    # Path to config file

# Database
export DATABASE_URL=postgresql://user:password@host:5432/overlord

# Redis
export REDIS_URL=redis://host:6379/0

# Trading
export TRADING_ENABLED=true
export WALBI_API_KEY=your_api_key
export WALBI_API_SECRET=your_api_secret

# Security (Grail Agent)
export GRAIL_SECRET_KEY=your_secret_key
export GRAIL_TOKEN_TTL=3600

# Monitoring
export PROMETHEUS_ENABLED=true
```

### Configuration File (YAML)

See `config/default.yaml` for full configuration options.

## 🌐 Deployment

### Automated CI/CD Deployment (Recommended)

**First-time setup**:
```bash
# Run automated setup wizard
./scripts/github-setup-automation.sh
```

**Regular deployments**:
```bash
# Deploy to staging
git push origin develop

# Deploy to production (with approval)
git push origin main
```

See [Quick Start CI/CD Guide](docs/deployment/QUICK_START_CI_CD.md) for detailed instructions.

### Manual Infrastructure Provisioning

```bash
# Initialize Terraform
cd terraform
terraform init

# Review infrastructure plan
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan
```

### Manual Kubernetes Deployment

```bash
# Using Helm
helm install overlord helm/overlord/ \
  --namespace overlord-production \
  --create-namespace \
  --values helm/overlord/values-production.yaml

# Verify deployment
kubectl get pods -n overlord-production
kubectl logs -f deployment/overlord -n overlord-production
```

## 📊 Monitoring

### Accessing Grafana

```bash
# Port-forward Grafana
kubectl port-forward -n overlord-monitoring svc/prometheus-grafana 3000:80

# Access at http://localhost:3000
```

### Key Metrics

- **Request Rate**: HTTP requests per second
- **Error Rate**: Failed requests percentage
- **Latency**: P50, P95, P99 response times
- **Trading Volume**: Orders executed per minute
- **Grail Agent**: Token validation rate, active sessions
- **Overlord Status**: Module health, initialization time
- **CI/CD**: Deployment frequency, success rate, duration

### Health Endpoints

```bash
# Root health check
curl http://localhost:8000/health

# Detailed status (includes Overlord + Grail)
curl http://localhost:8000/api/v1/status

# CI/CD pipeline status
gh run list --limit 10
```

## 📚 Documentation

### Repository Structure

```
.
├── .github/              # GitHub workflows & CI/CD
│   └── workflows/
│       └── ci-cd-full-cycle.yml
├── config/               # Configuration files
│   ├── default.yaml
│   └── production.yaml
├── docs/                 # Documentation
│   ├── deployment/
│   │   ├── QUICK_START_CI_CD.md
│   │   ├── github-actions-setup.md
│   │   ├── setup-checklist.md
│   │   ├── production-deployment.md
│   │   └── secrets-template.env
│   └── ...
├── helm/                 # Helm charts
├── k8s/                  # Kubernetes manifests
├── scripts/              # Automation scripts
│   ├── setup-ci-cd.sh
│   ├── github-setup-automation.sh
│   ├── validate-secrets.sh
│   ├── pre-deployment-checks.sh
│   └── smoke-tests.sh
├── src/                  # Application source
│   ├── analytics/
│   ├── api/
│   ├── auth/             # Auth & Grail Agent
│   │   ├── grail_agent.py
│   │   ├── token_validator.py
│   │   └── permissions.py
│   ├── core/             # Core modules
│   │   ├── bootstrap.py   # Overlord Bootstrap
│   │   ├── engine.py
│   │   ├── state_machine.py
│   │   └── config.py
│   ├── database/
│   ├── execution/
│   ├── market_data/
│   ├── models/
│   ├── risk/
│   ├── strategy/
│   └── main.py           # FastAPI application
├── tests/                # Test suite
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Standards

- **Formatting**: Black (line length: 120)
- **Linting**: Flake8, Pylint, MyPy
- **Testing**: Pytest with >80% coverage
- **Commit Messages**: Conventional Commits format

### CI/CD for Contributions

All pull requests automatically trigger:
- Quality gates (linting, formatting)
- Security scanning
- Unit + integration tests
- Docker build verification

## 🔐 Security

### Reporting Vulnerabilities

Please report security vulnerabilities via GitHub Security Advisories.

### Security Features

- ✅ Grail Agent token validation
- ✅ Session management with HMAC
- ✅ Blacklist for revoked tokens
- ✅ Audit logging
- ✅ Container scanning (Trivy)
- ✅ Dependency scanning (Snyk)
- ✅ Automated security updates (Dependabot)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Secured by Grail Agent
- Initialized by Overlord Bootstrap
- Deployed on [Kubernetes](https://kubernetes.io/)
- Monitored with [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/)
- Automated with [GitHub Actions](https://github.com/features/actions)

## 📦 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/legion14041981-ui/overlord-trading-system-v8/issues)
- **GitHub Actions**: [View CI/CD pipeline](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)
- **Repository Owner**: [legion14041981-ui](https://github.com/legion14041981-ui)

---

**Built with ❤️ by LEGION**  
**Version**: 8.1.0  
**Last Updated**: January 7, 2026

✅ **Grail Agent Security Layer Active**  
✅ **Overlord Bootstrap Initialized**  
✅ **CI/CD Pipeline Configured**  
✅ **Production Ready**
