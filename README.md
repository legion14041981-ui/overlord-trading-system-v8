# 🚀 Overlord v8.1 - Autonomous Trading System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-20.10+-2496ED.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Grail Agent](https://img.shields.io/badge/security-Grail%20Agent-green.svg)]()
[![CI/CD](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions/workflows/ci-cd-full-cycle.yml/badge.svg)](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)
[![Deployment](https://img.shields.io/badge/deployment-automated-success.svg)](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)

> Enterprise-grade autonomous trading system with multi-exchange integration, real-time risk management, and production-ready Docker-based infrastructure.
>
> **NEW in v8.1**: Integrated with **Grail Agent** security layer, **Overlord Bootstrap** initialization system, and **Full CI/CD Pipeline**

## 📋 Table of Contents

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
- 🚀 **Production Ready**: Docker-based deployment with auto-scaling
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

- **Docker**: Containerized deployment with multi-stage builds
- **Database**: PostgreSQL with automated backups
- **Caching**: Redis for session state and rate limiting
- **Monitoring**: Prometheus, Grafana, AlertManager

### DevOps

- **CI/CD**: GitHub Actions with automated testing
- **Security**: Trivy and Bandit scanning
- **Deployment**: Docker-based with multi-environment support
- **Orchestration**: Compatible with Docker Compose, Swarm, or any container orchestrator

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Walbi   │  │ Binance  │  │  Other   │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└────────┴─────────────┴─────────────┴─────────────────────┘
        │             │             │
        └─────────────┴─────────────────┘
                      │
        ┌─────────────┴─────────────────┐
        │   Reverse Proxy / LB       │
        │  (nginx, traefik, etc.)   │
        └─────────────┬─────────────────┘
                      │
        ┌─────────────┴─────────────────┐
        │   Overlord Trading API    │
        │  ┌──────────────────────┐ │
        │  │ Overlord Bootstrap  │ │  ← Initialization system
        │  │ Grail Agent Security│ │  ← Token validation
        │  │ Trading Engine      │ │  ← Order execution
        │  │ Risk Management     │ │  ← Risk controls
        │  └──────────────────────┘ │
        └─────┴──────────────┬──────┘
              │              │
    ┌─────────┴────┐  ┌──────┴──────┐
    │ PostgreSQL   │  │    Redis    │
    │  (Database)  │  │  (Cache)    │
    └──────────────┘  └─────┴───────┐
              │              │
    ┌─────────┴─────────┐  │
    │  Prometheus Metrics   │  │
    └─────────┬─────────┘  │
              │              │
    ┌─────────┴─────────┐  │
    │   Grafana Dashboards  │  │
    └─────────────────────┘  │
                              │
        All running in Docker containers
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
- ✅ **5-stage pipeline**: Quality → Security → Testing → Build → Push
- ✅ **Docker-only deployment**: Build → Test → Push to GHCR
- ✅ **Multi-environment support**: Staging (develop) + Production (main)
- ✅ **Container scanning**: Trivy security scanning
- ✅ **Automated testing**: Unit + Integration tests with PostgreSQL & Redis

### Pipeline Stages

```mermaid
graph LR
    A[Quality Gates] --> B[Security Scanning]
    B --> C[Unit Tests]
    C --> D[Integration Tests]
    D --> E[Docker Build & Push]
    E --> F[Container Scanning]
    F --> G[🚀 Image Ready]
```

### Deployment Workflow

**Staging (Auto-deploy on `develop` branch)**:
```bash
git push origin develop
# → Auto-triggers pipeline
# → Builds Docker image
# → Pushes to ghcr.io with 'staging' tag
```

**Production (Auto-deploy on `main` branch)**:
```bash
git push origin main
# → Pipeline runs all tests
# → Builds Docker image
# → Pushes to ghcr.io with 'latest' tag
```

### Running Locally

```bash
# Pull latest image from registry
docker pull ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest

# Run container
docker run -d \
  --name overlord-v8 \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest
```

---

## 📦 Prerequisites

### Local Development

- Python 3.11+
- Docker 20.10+
- Docker Compose (optional, for local stack)

### Cloud Infrastructure (Optional)

- Container hosting platform (AWS ECS, Google Cloud Run, DigitalOcean, etc.)
- PostgreSQL database (managed or self-hosted)
- Redis cache (managed or self-hosted)

### CI/CD Setup

- GitHub repository with Actions enabled
- GitHub Container Registry (automatically available)

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
# Start all services (Overlord + PostgreSQL + Redis + Prometheus + Grafana)
docker-compose up -d

# Check logs
docker-compose logs -f overlord

# Access API
curl http://localhost:8000/health

# Access Grafana (optional)
open http://localhost:3000

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

### CI/CD Deployment (Recommended)

The system automatically builds and publishes Docker images on every push to `main` or `develop` branches.

**Pull and run latest image**:
```bash
# Production (main branch)
docker pull ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest

# Staging (develop branch)
docker pull ghcr.io/legion14041981-ui/overlord-trading-system-v8:staging

# Run with environment variables
docker run -d \
  --name overlord \
  -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  -e OVERLORD_MODE=standard \
  ghcr.io/legion14041981-ui/overlord-trading-system-v8:latest
```

### Docker Compose Deployment

```bash
# Production stack
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Manual Build

```bash
# Build image
docker build -t overlord:v8.1 .

# Run locally
docker run -d -p 8000:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  overlord:v8.1
```

## 📊 Monitoring

### Health Endpoints

```bash
# Root health check
curl http://localhost:8000/health

# Detailed status (includes Overlord + Grail)
curl http://localhost:8000/api/v1/status

# Prometheus metrics
curl http://localhost:8000/metrics
```

### Accessing Grafana (when using docker-compose)

```bash
# Grafana is available at http://localhost:3000
# Default credentials: admin/admin

# Or port-forward if running separately
docker run -d -p 3000:3000 \
  -e GF_SERVER_ROOT_URL=http://localhost:3000 \
  grafana/grafana
```

### Key Metrics

- **Request Rate**: HTTP requests per second
- **Error Rate**: Failed requests percentage
- **Latency**: P50, P95, P99 response times
- **Trading Volume**: Orders executed per minute
- **Grail Agent**: Token validation rate, active sessions
- **Overlord Status**: Module health, initialization time

## 📚 Documentation

### Repository Structure

```
.
├── .github/              # GitHub workflows & CI/CD
│   └── workflows/
│       ├── ci.yml
│       ├── ci-enhanced.yml
│       ├── ci-cd-full-cycle.yml
│       └── deploy.yml
├── config/               # Configuration files
│   ├── default.yaml
│   └── production.yaml
├── docs/                 # Documentation
├── scripts/              # Automation scripts
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
- **Testing**: Pytest with >70% coverage
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
- ✅ Dependency scanning (Bandit, Safety)
- ✅ Automated security updates (Dependabot)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Secured by Grail Agent
- Initialized by Overlord Bootstrap
- Containerized with [Docker](https://www.docker.com/)
- Monitored with [Prometheus](https://prometheus.io/) & [Grafana](https://grafana.com/)
- Automated with [GitHub Actions](https://github.com/features/actions)

## 📦 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/legion14041981-ui/overlord-trading-system-v8/issues)
- **GitHub Actions**: [View CI/CD pipeline](https://github.com/legion14041981-ui/overlord-trading-system-v8/actions)
- **Repository Owner**: [legion14041981-ui](https://github.com/legion14041981-ui)

---

**Built with ❤️ by LEGION**  
**Version**: 8.1.0  
**Last Updated**: January 8, 2026

✅ **Grail Agent Security Layer Active**  
✅ **Overlord Bootstrap Initialized**  
✅ **CI/CD Pipeline Configured**  
✅ **Production Ready**  
✅ **Docker-Based Deployment**  
❌ **Kubernetes: OUT OF SCOPE (v8.1)**
