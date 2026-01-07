# Manual Secret Rotation Runbook

**Track**: [SEC-003] Automated Secret Rotation  
**Owner**: Security Team  
**Last Updated**: 2026-01-07

---

## 📋 Overview

This runbook describes the manual procedure for rotating secrets in OVERLORD v8 when the automated CronJob fails or when immediate rotation is required.

## ⚠️ Prerequisites

- AWS CLI configured with SecretsManager permissions
- `kubectl` access to production cluster (namespace: `overlord`)
- PostgreSQL admin credentials
- PagerDuty incident created (for production)

---

## 🔄 Rotation Procedure

### Step 1: Generate New Password

```bash
NEW_PASSWORD=$(openssl rand -base64 32)
echo "$NEW_PASSWORD" > /tmp/new_password.txt  # Backup securely
echo "✅ New password generated"
```

### Step 2: Update AWS Secrets Manager

```bash
aws secretsmanager update-secret \
  --secret-id overlord/database \
  --secret-string "{\"username\":\"overlord\",\"password\":\"$NEW_PASSWORD\"}" \
  --region us-east-1

if [ $? -eq 0 ]; then
  echo "✅ AWS Secrets Manager updated"
else
  echo "❌ Failed to update AWS Secrets Manager"
  exit 1
fi
```

### Step 3: Update Database Password

```bash
# Get current password from Kubernetes secret
OLD_PASSWORD=$(kubectl get secret postgres-credentials -n overlord \
  -o jsonpath='{.data.password}' | base64 -d)

# Update database
PGPASSWORD="$OLD_PASSWORD" psql \
  -h prod-db.overlord.internal \
  -U postgres \
  -d postgres \
  -c "ALTER USER overlord PASSWORD '$NEW_PASSWORD';"

if [ $? -eq 0 ]; then
  echo "✅ Database password updated"
else
  echo "❌ Failed to update database password"
  exit 1
fi
```

### Step 4: Force External Secrets Sync

```bash
kubectl annotate externalsecret overlord-db-credentials \
  force-sync="$(date +%s)" \
  --overwrite \
  -n overlord

echo "⏳ Waiting for External Secrets to sync..."
sleep 15

# Verify secret updated
NEW_SECRET_PASSWORD=$(kubectl get secret postgres-credentials -n overlord \
  -o jsonpath='{.data.password}' | base64 -d)

if [ "$NEW_SECRET_PASSWORD" == "$NEW_PASSWORD" ]; then
  echo "✅ Kubernetes secret updated"
else
  echo "❌ Secret not synced. Check External Secrets Operator logs"
  exit 1
fi
```

### Step 5: Rolling Restart of API Pods

```bash
kubectl rollout restart deployment/overlord-api -n overlord

echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/overlord-api -n overlord --timeout=5m

if [ $? -eq 0 ]; then
  echo "✅ API pods restarted successfully"
else
  echo "❌ Rollout failed. Check pod logs"
  exit 1
fi
```

### Step 6: Verify Connectivity

```bash
# Test database connection with new credentials
kubectl exec -it deploy/overlord-api -n overlord -- \
  psql -h postgres.overlord.svc.cluster.local -U overlord -d overlord -c "SELECT 1;"

if [ $? -eq 0 ]; then
  echo "✅ Database connectivity verified"
else
  echo "❌ Database connection failed. Initiating rollback..."
  # See Rollback section below
  exit 1
fi
```

### Step 7: Update Metrics

```bash
# Push success metric to Prometheus
cat <<EOF | curl --data-binary @- \
  http://prometheus-pushgateway.monitoring.svc.cluster.local:9091/metrics/job/secret-rotation
overlord_secret_rotation_failed 0
overlord_secret_last_rotation_timestamp $(date +%s)
EOF

echo "✅ Metrics updated"
```

---

## 🔙 Rollback Procedure

If rotation fails, revert to the previous secret version:

```bash
# Retrieve previous secret version from AWS
PREVIOUS_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id overlord/database \
  --version-stage AWSPREVIOUS \
  --region us-east-1 \
  --query SecretString \
  --output text)

OLD_PASSWORD=$(echo "$PREVIOUS_SECRET" | jq -r '.password')

# Restore previous password in database
PGPASSWORD="$NEW_PASSWORD" psql \
  -h prod-db.overlord.internal \
  -U postgres \
  -d postgres \
  -c "ALTER USER overlord PASSWORD '$OLD_PASSWORD';"

# Restore previous version in AWS
aws secretsmanager update-secret \
  --secret-id overlord/database \
  --secret-string "$PREVIOUS_SECRET" \
  --region us-east-1

# Force re-sync
kubectl annotate externalsecret overlord-db-credentials \
  force-sync="$(date +%s)" \
  --overwrite \
  -n overlord

# Restart pods
kubectl rollout restart deployment/overlord-api -n overlord

echo "✅ Rollback completed"
```

---

## 📊 Post-Rotation Checklist

- [ ] Database connectivity verified
- [ ] All API pods healthy
- [ ] No error alerts in Prometheus
- [ ] Application logs clean (no auth errors)
- [ ] PagerDuty incident resolved
- [ ] Post-mortem created (if manual rotation was emergency)

---

## 🚨 Troubleshooting

### External Secrets Not Syncing

```bash
# Check External Secrets Operator logs
kubectl logs -n external-secrets-system deploy/external-secrets

# Check ExternalSecret status
kubectl describe externalsecret overlord-db-credentials -n overlord
```

### Database Connection Refused

```bash
# Verify database is reachable
kubectl exec -it deploy/overlord-api -n overlord -- \
  nc -zv postgres.overlord.svc.cluster.local 5432

# Check PostgreSQL logs
kubectl logs -n overlord statefulset/postgres --tail=50
```

### API Pods CrashLoopBackOff

```bash
# Check pod logs
kubectl logs -n overlord deploy/overlord-api --tail=100

# Describe pod for events
kubectl describe pod -n overlord -l app=overlord-api
```

---

## 📚 References

- [AWS Secrets Manager CLI](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/)
- [External Secrets Operator Docs](https://external-secrets.io/)
- [PostgreSQL Password Management](https://www.postgresql.org/docs/current/sql-alterrole.html)

---

**Emergency Contact**: @security-team on Slack  
**On-Call**: PagerDuty rotation
