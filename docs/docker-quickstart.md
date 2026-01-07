# Docker Quickstart Guide

**Track**: [DEP-001] Docker Multi-Stage Build Optimization  
**Date**: 2026-01-07

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8 GB RAM available
- 20 GB disk space

### Start OVERLORD Stack

```bash
# Clone repository
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Start all services
make up

# Wait for services to be healthy (~30 seconds)
# Check status
make health
```

**Services Available**:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9091
- **Jaeger**: http://localhost:16686

---

## 📦 Development Workflow

### Build Images

```bash
# Build development image (with hot-reload)
make build

# Build production image (optimized)
make build-prod

# Check image size
docker images overlord-api
```

**Expected Sizes**:
- Development: ~500 MB
- Production: **~150 MB** ✅

### Start Services

```bash
# Start in detached mode
make up

# Start with logs visible
docker-compose up

# Start specific service
docker-compose up -d api
```

### View Logs

```bash
# All services
make logs

# API only
make logs-api

# Follow logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Access Containers

```bash
# Shell in API container
make shell

# Root shell (for debugging)
make shell-root

# PostgreSQL shell
make shell-db
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With coverage report
make test-coverage
```

### Linting & Formatting

```bash
# Run linters
make lint

# Auto-format code
make format
```

---

## 🗄️ Database Operations

### Migrations

```bash
# Run pending migrations
make migrate

# Create new migration
make migrate-create MSG="add user table"

# Rollback last migration
make migrate-rollback

# View migration history
docker-compose exec api alembic history
```

### Manual Database Access

```bash
# Connect to PostgreSQL
make shell-db

# Inside psql:
\dt                 # List tables
\d trades          # Describe trades table
SELECT * FROM trades LIMIT 10;
```

---

## 🔒 Security Scanning

### Vulnerability Scanning

```bash
# Scan for all vulnerabilities
make scan

# Scan for HIGH/CRITICAL only (fail on findings)
make scan-high

# Scan specific image
docker run --rm aquasec/trivy image overlord-api:latest
```

### Security Best Practices

✅ **Implemented**:
- Non-root user (`overlord`)
- Minimal base image (`python:3.11-slim`)
- No hardcoded secrets
- Read-only root filesystem (planned)
- Health checks configured
- Security headers in Ingress

---

## ☁️ AWS ECR Deployment

### Push to ECR

```bash
# Login to ECR
make ecr-login

# Build and push
make ecr-push

# Manual steps
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

docker tag overlord-api:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/overlord-api:latest

docker push \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/overlord-api:latest
```

---

## 🧹 Cleanup

### Stop Services

```bash
# Stop all services
make down

# Stop and remove volumes
docker-compose down -v
```

### Remove Images

```bash
# Clean stopped containers and dangling images
make clean

# Remove ALL Docker data (⚠️ DANGEROUS)
make clean-all
```

---

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Change host port
```

### Service Won't Start

```bash
# Check logs
make logs-api

# Inspect container
docker-compose ps
docker inspect overlord-api

# Check health
docker-compose exec api curl http://localhost:8000/health
```

### Database Connection Issues

```bash
# Test PostgreSQL connectivity
docker-compose exec api nc -zv postgres 5432

# Check environment variables
docker-compose exec api env | grep DATABASE

# Restart database
docker-compose restart postgres
```

### Build Failures

```bash
# Clear Docker build cache
docker builder prune -a -f

# Rebuild without cache
docker-compose build --no-cache

# Check disk space
df -h
docker system df
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Allocate more resources to Docker Desktop:
# Settings → Resources → increase CPU/Memory

# Reduce service replicas for local dev
# In docker-compose.yml, remove 'deploy' section
```

---

## 📊 Monitoring

### Prometheus Metrics

```bash
# View metrics endpoint
curl http://localhost:9090/metrics

# Open Prometheus UI
make metrics

# Query examples:
# - overlord_api_requests_total
# - overlord_api_request_duration_seconds
# - overlord_db_connections_active
```

### Grafana Dashboards

```bash
# Open Grafana
make dashboard

# Default credentials: admin/admin
# Change password on first login

# Import dashboard:
# 1. Click + → Import
# 2. Upload JSON from grafana/dashboards/
# 3. Select Prometheus datasource
```

### Distributed Tracing

```bash
# Open Jaeger UI
make tracing

# View traces:
# 1. Select 'overlord-api' service
# 2. Click 'Find Traces'
# 3. Inspect trace details
```

---

## 🎯 Performance Tips

### Build Optimization

1. **Layer Caching**
   ```bash
   # Leverage BuildKit cache
   export DOCKER_BUILDKIT=1
   docker build --cache-from overlord-api:latest .
   ```

2. **Multi-Platform Builds**
   ```bash
   # Build for multiple architectures
   docker buildx build \
     --platform linux/amd64,linux/arm64 \
     -t overlord-api:latest .
   ```

3. **Parallel Builds**
   ```bash
   # Build services in parallel
   docker-compose build --parallel
   ```

### Runtime Optimization

1. **Resource Limits**
   ```yaml
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         cpus: '2.0'
         memory: 2G
   ```

2. **Volume Mounts for Hot-Reload**
   ```yaml
   volumes:
     - ./src:/app/src  # Code changes reload instantly
   ```

3. **Healthcheck Tuning**
   ```yaml
   healthcheck:
     interval: 30s      # Adjust based on needs
     timeout: 5s
     retries: 3
     start_period: 10s
   ```

---

## 📚 Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Trivy Security Scanner](https://aquasecurity.github.io/trivy/)

---

**Next**: [Kubernetes Deployment Guide](./kubernetes-deployment.md)
