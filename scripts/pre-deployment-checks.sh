#!/bin/bash
# ==============================================================================
# Overlord v8.1 - Pre-Deployment Automated Checks
# ==============================================================================
# Description: Comprehensive verification before production deployment
# Exit Codes: 0 (success), 1 (failure)
# ==============================================================================

set -euo pipefail

# Configuration
ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((CHECKS_WARNING++))
}

# ==============================================================================
# Phase 1: Infrastructure Checks
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 1: INFRASTRUCTURE CHECKS ===${NC}"

# Check Kubernetes cluster
if kubectl cluster-info > /dev/null 2>&1; then
    check_pass "Kubernetes cluster is accessible"
else
    check_fail "Cannot access Kubernetes cluster"
fi

# Check namespace exists
if kubectl get namespace "overlord-${ENVIRONMENT}" > /dev/null 2>&1; then
    check_pass "${ENVIRONMENT} namespace exists"
else
    check_fail "${ENVIRONMENT} namespace does not exist"
fi

# Check node count
NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
if [ "$NODE_COUNT" -ge 3 ]; then
    check_pass "Minimum 3 nodes available ($NODE_COUNT nodes)"
else
    check_fail "Insufficient nodes ($NODE_COUNT, need 3+)"
fi

# Check node resources
if kubectl top nodes > /dev/null 2>&1; then
    check_pass "Node metrics available"
else
    check_warn "Node metrics not available (Metrics Server not installed?)"
fi

# ==============================================================================
# Phase 2: Database Checks
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 2: DATABASE CHECKS ===${NC}"

# Check PostgreSQL connectivity
if kubectl exec -it $(kubectl get pods -n overlord-${ENVIRONMENT} -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) -- pg_isready > /dev/null 2>&1; then
    check_pass "PostgreSQL database is accessible"
else
    check_warn "Could not verify PostgreSQL connectivity"
fi

# Check database backups
LATEST_BACKUP=$(aws s3 ls s3://overlord-backups/ --recursive 2>/dev/null | tail -1 || echo "")
if [ -n "$LATEST_BACKUP" ]; then
    check_pass "Recent database backup exists"
else
    check_warn "Could not verify recent database backup"
fi

# ==============================================================================
# Phase 3: Secrets & Configuration
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 3: SECRETS & CONFIGURATION ===${NC}"

# Check secrets exist
if kubectl get secret overlord-secrets -n "overlord-${ENVIRONMENT}" > /dev/null 2>&1; then
    check_pass "Application secrets exist"
else
    check_fail "Application secrets not found"
fi

# Check ConfigMap exists
if kubectl get configmap overlord-config -n "overlord-${ENVIRONMENT}" > /dev/null 2>&1; then
    check_pass "Application configuration exists"
else
    check_fail "Application configuration not found"
fi

# Check TLS certificate
TLS_EXPIRY=$(kubectl get secret overlord-tls -n "overlord-${ENVIRONMENT}" -o jsonpath='{.data.tls\.crt}' 2>/dev/null | base64 -d | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "")
if [ -n "$TLS_EXPIRY" ]; then
    EXPIRY_EPOCH=$(date -d "$TLS_EXPIRY" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    
    if [ "$DAYS_LEFT" -gt 30 ]; then
        check_pass "TLS certificate valid for $DAYS_LEFT more days"
    elif [ "$DAYS_LEFT" -gt 0 ]; then
        check_warn "TLS certificate expires in $DAYS_LEFT days"
    else
        check_fail "TLS certificate has expired"
    fi
else
    check_warn "Could not check TLS certificate"
fi

# ==============================================================================
# Phase 4: External Services
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 4: EXTERNAL SERVICES ===${NC}"

# Check Walbi API connectivity
if timeout 5 curl -sf https://api.walbi.example.com/health > /dev/null 2>&1; then
    check_pass "Walbi API is accessible"
else
    check_warn "Could not reach Walbi API (may be in different network)"
fi

# Check S3 connectivity
if aws s3 ls s3://overlord-backups --region us-east-1 > /dev/null 2>&1; then
    check_pass "S3 bucket is accessible"
else
    check_warn "Could not verify S3 access"
fi

# ==============================================================================
# Phase 5: Monitoring Stack
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 5: MONITORING STACK ===${NC}"

# Check Prometheus
if kubectl get pod -n overlord-monitoring -l app=prometheus > /dev/null 2>&1; then
    check_pass "Prometheus is deployed"
else
    check_fail "Prometheus not found"
fi

# Check Grafana
if kubectl get pod -n overlord-monitoring -l app=grafana > /dev/null 2>&1; then
    check_pass "Grafana is deployed"
else
    check_fail "Grafana not found"
fi

# Check AlertManager
if kubectl get pod -n overlord-monitoring -l app=alertmanager > /dev/null 2>&1; then
    check_pass "AlertManager is deployed"
else
    check_warn "AlertManager not found"
fi

# ==============================================================================
# Phase 6: Container Registry
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 6: CONTAINER REGISTRY ===${NC}"

# Check image exists in registry
if docker manifest inspect "ghcr.io/legion14041981-ui/overlord-trading-system-v8:${VERSION}" > /dev/null 2>&1; then
    check_pass "Docker image found (overlord:${VERSION})"
else
    check_fail "Docker image not found (overlord:${VERSION})"
fi

# ==============================================================================
# Phase 7: Documentation Verification
# ==============================================================================
echo -e "${BLUE}\n=== PHASE 7: DOCUMENTATION VERIFICATION ===${NC}"

# Check runbooks exist
RUNBOOK_COUNT=$(find docs/runbooks -name 'e-*.md' 2>/dev/null | wc -l)
if [ "$RUNBOOK_COUNT" -ge 9 ]; then
    check_pass "All runbooks exist ($RUNBOOK_COUNT found)"
else
    check_fail "Missing runbooks ($RUNBOOK_COUNT found, need 9+)"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${BLUE}\n=== DEPLOYMENT READINESS SUMMARY ===${NC}"
echo -e "${GREEN}Passed:   $CHECKS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $CHECKS_WARNING${NC}"
echo -e "${RED}Failed:   $CHECKS_FAILED${NC}"
echo

if [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ System is ready for deployment${NC}"
    exit 0
else
    echo -e "${RED}⚠️ Deployment blocked due to $CHECKS_FAILED critical issues${NC}"
    exit 1
fi
