# Deployment Guide

## Overview

This guide covers deployment strategies for Overlord Trading System v8 across different environments and platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Monitoring Setup](#monitoring-setup)
- [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB SSD
- OS: Ubuntu 20.04+, CentOS 8+, or any Linux with Docker support

**Recommended:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 50+ GB NVMe SSD
- OS: Ubuntu 22.04 LTS

### Software Dependencies

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker 24+
- Docker Compose 2.20+
- Kubernetes 1.28+ (for K8s deployment)

---

## Environment Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Application
APP_NAME="Overlord Trading System"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/overlord
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Security
SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Trading
BINANCE_API_KEY=your-binance-api-key
BINANCE_API_SECRET=your-binance-api-secret
BYBIT_API_KEY=your-bybit-api-key
BYBIT_API_SECRET=your-bybit-api-secret

# Risk Management
MAX_POSITION_SIZE=10000
MAX_DAILY_LOSS=1000
MAX_DRAWDOWN=0.15

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

### Secrets Management

**For production, use a secrets manager:**

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name overlord-trading/production \
  --secret-string file://secrets.json

# Kubernetes Secrets
kubectl create secret generic overlord-secrets \
  --from-env-file=.env.production \
  --namespace=overlord-trading

# Docker Swarm Secrets
echo "$BINANCE_API_KEY" | docker secret create binance_api_key -
```

---

## Local Development

### Standard Setup

```bash
# 1. Clone and setup
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your values

# 5. Start dependencies
docker-compose -f docker-compose.dev.yml up -d postgres redis

# 6. Run migrations
alembic upgrade head

# 7. Start application
uvicorn src.main:app --reload --port 8000
```

### Development with Hot Reload

```bash
# Using uvicorn with auto-reload
uvicorn src.main:app \
  --reload \
  --reload-dir src \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level debug
```

---

## Docker Deployment

### Single Host Production

```bash
# 1. Build image
docker build -t overlord-trading:latest -f docker/Dockerfile .

# 2. Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f api

# 5. Scale API instances
docker-compose up -d --scale api=3
```

### Docker Compose Production File

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  api:
    image: overlord-trading:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/overlord
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - overlord-network
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  postgres:
    image: postgres:15-alpine
    restart: always
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=overlord
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=secure-password
    networks:
      - overlord-network

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - overlord-network

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - overlord-network

volumes:
  postgres-data:
  redis-data:

networks:
  overlord-network:
    driver: bridge
```

### Docker Swarm Deployment

```bash
# 1. Initialize swarm
docker swarm init

# 2. Create secrets
echo "$BINANCE_API_KEY" | docker secret create binance_api_key -
echo "$BINANCE_API_SECRET" | docker secret create binance_api_secret -

# 3. Deploy stack
docker stack deploy -c docker-compose.swarm.yml overlord

# 4. Check services
docker stack services overlord

# 5. Scale services
docker service scale overlord_api=5

# 6. Update service
docker service update \
  --image overlord-trading:v2.0.0 \
  overlord_api
```

---

## Kubernetes Deployment

### Basic Deployment

```bash
# 1. Create namespace
kubectl create namespace overlord-trading

# 2. Apply secrets
kubectl apply -f k8s/secrets.yaml -n overlord-trading

# 3. Apply configmaps
kubectl apply -f k8s/configmap.yaml -n overlord-trading

# 4. Deploy database
kubectl apply -f k8s/postgres.yaml -n overlord-trading

# 5. Deploy Redis
kubectl apply -f k8s/redis.yaml -n overlord-trading

# 6. Deploy API
kubectl apply -f k8s/api-deployment.yaml -n overlord-trading

# 7. Create service
kubectl apply -f k8s/api-service.yaml -n overlord-trading

# 8. Setup ingress
kubectl apply -f k8s/ingress.yaml -n overlord-trading
```

### Helm Chart Deployment

```bash
# 1. Add Helm repo (if chart is published)
helm repo add overlord https://charts.overlord-trading.io
helm repo update

# 2. Install with custom values
helm install overlord-trading overlord/overlord \
  --namespace overlord-trading \
  --create-namespace \
  --values values.production.yaml

# 3. Upgrade
helm upgrade overlord-trading overlord/overlord \
  --namespace overlord-trading \
  --values values.production.yaml

# 4. Rollback
helm rollback overlord-trading 1 --namespace overlord-trading
```

### Kubernetes Manifests Example

**api-deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overlord-api
  namespace: overlord-trading
spec:
  replicas: 3
  selector:
    matchLabels:
      app: overlord-api
  template:
    metadata:
      labels:
        app: overlord-api
    spec:
      containers:
      - name: api
        image: overlord-trading:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: overlord-secrets
              key: database-url
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## Cloud Platforms

### AWS ECS

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name overlord-trading

# 2. Build and push image
$(aws ecr get-login --no-include-email)
docker build -t overlord-trading .
docker tag overlord-trading:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/overlord-trading:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/overlord-trading:latest

# 3. Create task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 4. Create service
aws ecs create-service \
  --cluster overlord-cluster \
  --service-name overlord-api \
  --task-definition overlord-api:1 \
  --desired-count 3
```

### Google Cloud Run

```bash
# 1. Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/overlord-trading

# 2. Deploy to Cloud Run
gcloud run deploy overlord-api \
  --image gcr.io/PROJECT_ID/overlord-trading \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL
```

### Azure Container Instances

```bash
# 1. Create container registry
az acr create --name overlordregistry --resource-group overlord-rg --sku Basic

# 2. Build and push
az acr build --registry overlordregistry --image overlord-trading:latest .

# 3. Deploy container
az container create \
  --resource-group overlord-rg \
  --name overlord-api \
  --image overlordregistry.azurecr.io/overlord-trading:latest \
  --dns-name-label overlord-api \
  --ports 8000
```

---

## Monitoring Setup

### Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'overlord-api'
    static_configs:
      - targets: ['api:8000']
```

### Grafana

```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard.json
```

---

## Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

pg_dump -h postgres -U user overlord | gzip > $BACKUP_DIR/overlord_$DATE.sql.gz

# Retention: keep last 30 days
find $BACKUP_DIR -name "overlord_*.sql.gz" -mtime +30 -delete
```

### Restore from Backup

```bash
# Restore database
gunzip -c overlord_20260108_065000.sql.gz | psql -h postgres -U user overlord
```

---

## Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/metrics

# Database connectivity
psql -h localhost -U user -d overlord -c "SELECT 1;"
```

---

## Troubleshooting

### Common Issues

1. **Database connection failures**:
   ```bash
   # Check PostgreSQL logs
   docker logs overlord-postgres
   ```

2. **High memory usage**:
   ```bash
   # Check container stats
   docker stats overlord-api
   ```

3. **API timeouts**:
   ```bash
   # Increase worker count
   export API_WORKERS=8
   ```

---

For more information, see [API Documentation](API.md) and [Architecture Guide](ARCHITECTURE.md).
