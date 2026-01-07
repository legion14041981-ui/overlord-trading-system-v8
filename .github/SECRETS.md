# 🔐 GitHub Secrets Configuration Guide

## Required Secrets для CI/CD Pipeline

### 🎯 Container Registry

| Secret Name | Description | Example |
|-------------|-------------|----------|
| `GITHUB_TOKEN` | Автоматически предоставляется | `ghp_xxx...` |

### ☸️ Kubernetes Access

| Secret Name | Description | Generation Command |
|-------------|-------------|--------------------|
| `KUBECONFIG_STAGING` | Base64-encoded kubeconfig for staging | `cat ~/.kube/config \| base64 -w 0` |
| `KUBECONFIG_PRODUCTION` | Base64-encoded kubeconfig for production | `cat ~/.kube/config-prod \| base64 -w 0` |

### 🔒 Application Secrets (Staging)

```bash
# Create Kubernetes secret in staging namespace
kubectl create secret generic overlord-secrets \
  --from-literal=database-url="postgresql://user:pass@host:5432/overlord_staging" \
  --from-literal=redis-url="redis://:pass@host:6379/0" \
  --from-literal=api-key="staging-api-key-xxx" \
  -n overlord-staging
```

### 🔒 Application Secrets (Production)

```bash
# Create Kubernetes secret in production namespace
kubectl create secret generic overlord-secrets \
  --from-literal=database-url="postgresql://user:pass@host:5432/overlord_prod" \
  --from-literal=redis-url="redis://:pass@host:6379/0" \
  --from-literal=api-key="production-api-key-xxx" \
  --from-literal=sentry-dsn="https://xxx@sentry.io/xxx" \
  -n overlord-production
```

### 📧 Notifications

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | [Slack Apps](https://api.slack.com/messaging/webhooks) |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL (optional) | Server Settings > Integrations |

### 💡 Best Practices

1. **Rotation Policy**: Ротация secrets каждые 90 дней
2. **Least Privilege**: Минимальные права доступа
3. **Separate Envs**: Разные secrets для staging/production
4. **Encryption**: Использовать encrypted secrets GitHub
5. **Audit**: Регулярный audit использования

### 🛠️ Setup Commands

```bash
# Add secret to GitHub repository
gh secret set SECRET_NAME --body "SECRET_VALUE"

# Add secret from file
gh secret set KUBECONFIG_STAGING < kubeconfig-staging.txt

# List all secrets
gh secret list

# Delete secret
gh secret delete SECRET_NAME
```

### ✅ Validation Checklist

- [ ] All required secrets configured
- [ ] Kubeconfig files tested
- [ ] Database connections verified
- [ ] Slack webhook tested
- [ ] Secrets encrypted in GitHub
- [ ] Documentation updated
- [ ] Team access granted
- [ ] Rotation schedule documented
