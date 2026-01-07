# Kubernetes Deployment Guide

**Track**: [DEP-002] Kubernetes Helm Chart Development  
**Date**: 2026-01-07

---

## 🛡️ Обзор

Этот гайд покрывает развертывание **OVERLORD v8** в Kubernetes с использованием Helm.

### Ключевые возможности:
- ✅ Production-ready Helm chart
- ✅ Автоматическое масштабирование (HPA)
- ✅ Высокая доступность (PDB)
- ✅ HTTPS с автоматическими TLS сертификатами
- ✅ Prometheus мониторинг
- ✅ Network policies для безопасности
- ✅ Поддержка нескольких окружений (staging/production)

---

## 📍 Предварительные требования

### 1. Kubernetes кластер

```bash
# AWS EKS (рекомендуется)
eksctl create cluster \
  --name overlord-cluster \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name overlord-nodes \
  --node-type c6i.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10

# Или Google GKE
gcloud container clusters create overlord-cluster \
  --num-nodes=3 \
  --machine-type=n2-standard-4

# Или локальный minikube
minikube start --cpus=4 --memory=8192
```

### 2. Установка Helm

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Проверка
helm version
```

### 3. Необходимые компоненты

```bash
# NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.metrics.enabled=true

# cert-manager (для TLS сертификатов)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Prometheus Operator (опционально)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

---

## 🚀 Быстрый старт (10 минут)

### Шаг 1: Подготовка

```bash
# Клонирование репозитория
git clone https://github.com/legion14041981-ui/overlord-trading-system-v8.git
cd overlord-trading-system-v8

# Проверка подключения к кластеру
kubectl cluster-info
kubectl get nodes
```

### Шаг 2: Создание namespace

```bash
kubectl create namespace overlord-staging
kubectl create namespace overlord-production
```

### Шаг 3: Создание secrets

```bash
# PostgreSQL password
kubectl create secret generic postgres-password \
  --from-literal=password='your-secure-password' \
  --namespace overlord-staging

# Redis password
kubectl create secret generic redis-password \
  --from-literal=password='your-redis-password' \
  --namespace overlord-staging

# ECR registry credentials (AWS)
kubectl create secret docker-registry ecr-registry-secret \
  --docker-server=123456789012.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --namespace overlord-staging
```

### Шаг 4: Установка Helm chart

```bash
# Staging
helm install overlord ./helm/overlord \
  --namespace overlord-staging \
  --values helm/overlord/values-staging.yaml \
  --create-namespace

# Проверка статуса
helm status overlord -n overlord-staging
kubectl get pods -n overlord-staging -w
```

### Шаг 5: Проверка работы

```bash
# Port-forward для локального доступа
kubectl port-forward svc/overlord 8000:80 -n overlord-staging

# Проверка health endpoint
curl http://localhost:8000/health

# Открыть документацию API
open http://localhost:8000/docs
```

---

## 🛠️ Production Deployment

### 1. Подготовка внешних сервисов

#### AWS RDS PostgreSQL

```bash
# Создание RDS инстанса
aws rds create-db-instance \
  --db-instance-identifier overlord-prod-db \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 16.1 \
  --master-username overlord \
  --master-user-password 'SecurePassword123!' \
  --allocated-storage 100 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 30
```

#### AWS ElastiCache Redis

```bash
# Создание ElastiCache кластера
aws elasticache create-replication-group \
  --replication-group-id overlord-prod-redis \
  --replication-group-description "OVERLORD Production Redis" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled
```

### 2. Secrets Management

```bash
# Создание production secrets
kubectl create secret generic overlord-secrets \
  --from-literal=DATABASE_URL='postgresql://overlord:password@overlord-prod.abcdef.us-east-1.rds.amazonaws.com:5432/overlord' \
  --from-literal=REDIS_URL='redis://:password@overlord-prod.cache.amazonaws.com:6379/0' \
  --from-literal=API_KEY='your-api-key' \
  --from-literal=JWT_SECRET='your-jwt-secret' \
  --namespace overlord-production
```

### 3. Установка в Production

```bash
# Установка
helm install overlord ./helm/overlord \
  --namespace overlord-production \
  --values helm/overlord/values-production.yaml \
  --set image.tag="8.1.0" \
  --timeout 10m \
  --wait

# Проверка развертывания
kubectl rollout status deployment/overlord -n overlord-production
```

### 4. DNS Настройка

```bash
# Получение Ingress IP
kubectl get ingress -n overlord-production

# Создайте DNS A-запись:
# overlord.legion.ai -> <INGRESS_IP>
```

---

## 🔄 Обновление (Rolling Update)

### Стандартное обновление

```bash
# Обновление до новой версии
helm upgrade overlord ./helm/overlord \
  --namespace overlord-production \
  --values helm/overlord/values-production.yaml \
  --set image.tag="8.2.0" \
  --wait

# Мониторинг процесса
kubectl rollout status deployment/overlord -n overlord-production
```

### Rollback

```bash
# Откат к предыдущей версии
helm rollback overlord -n overlord-production

# Или к конкретной ревизии
helm rollback overlord 3 -n overlord-production
```

---

## 📊 Мониторинг

### Prometheus Метрики

```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Открыть UI
open http://localhost:9090

# Примеры запросов:
# rate(overlord_api_requests_total[5m])
# overlord_api_request_duration_seconds{quantile="0.99"}
```

### Grafana Dashboards

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Credentials: admin/prom-operator
open http://localhost:3000
```

### Логи

```bash
# Просмотр логов всех подов
kubectl logs -l app.kubernetes.io/name=overlord -n overlord-production --tail=100 -f

# Логи конкретного пода
kubectl logs overlord-5d7c8b9f4-abc12 -n overlord-production -f
```

---

## 🔧 Трублшутинг

### Pods не запускаются

```bash
# Диагностика
kubectl describe pod <pod-name> -n overlord-production
kubectl logs <pod-name> -n overlord-production
kubectl get events -n overlord-production --sort-by='.lastTimestamp'

# Проверка ресурсов
kubectl top pods -n overlord-production
kubectl top nodes
```

### ImagePullBackOff

```bash
# Проверка ECR credentials
kubectl get secret ecr-registry-secret -n overlord-production -o yaml

# Обновление credentials
kubectl delete secret ecr-registry-secret -n overlord-production
kubectl create secret docker-registry ecr-registry-secret \
  --docker-server=123456789012.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --namespace overlord-production
```

### Database подключение

```bash
# Тест подключения
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql postgresql://overlord:password@overlord-postgresql:5432/overlord

# Проверка NetworkPolicy
kubectl get networkpolicies -n overlord-production
```

### Проблемы с Ingress

```bash
# Проверка Ingress
kubectl describe ingress overlord -n overlord-production
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Проверка TLS сертификата
kubectl get certificate -n overlord-production
kubectl describe certificate overlord-production-tls -n overlord-production
```

---

## 🛡️ Лучшие практики

### 1. Безопасность

- ✅ **Используйте Secrets** для всех чувствительных данных
- ✅ **Network Policies** включены в production
- ✅ **Pod Security Standards** (runAsNonRoot, readOnlyRootFilesystem)
- ✅ **RBAC** для ServiceAccount
- ✅ **TLS** для всех внешних endpointов

### 2. Надежность

- ✅ **PodDisruptionBudget** для гарантированной доступности
- ✅ **Anti-affinity rules** для распределения по зонам
- ✅ **Health checks** (все 3 типа: liveness, readiness, startup)
- ✅ **Resource limits** установлены
- ✅ **Graceful shutdown** (terminationGracePeriodSeconds)

### 3. Масштабируемость

- ✅ **HPA** для автоматического масштабирования
- ✅ **Внешние сервисы** (RDS, ElastiCache) в production
- ✅ **Stateless архитектура**
- ✅ **Connection pooling**

### 4. Наблюдаемость

- ✅ **Prometheus metrics** экспортируются
- ✅ **ServiceMonitor** для автоматического discovery
- ✅ **Structured logging** (JSON)
- ✅ **Distributed tracing** (OpenTelemetry)

---

## 📚 Дополнительные ресурсы

- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [cert-manager](https://cert-manager.io/docs/)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)

---

**Следующий шаг**: [CI/CD Pipeline Setup](./cicd-pipeline.md)
