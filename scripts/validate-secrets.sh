#!/bin/bash

################################################################################
# Overlord v8.1 - Secrets Validation Script
################################################################################
# 
# This script validates that all required secrets are configured correctly
# and can connect to target resources.
# 
# Usage:
#   ./scripts/validate-secrets.sh [--staging|--production]
# 
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REPO_OWNER="legion14041981-ui"
REPO_NAME="overlord-trading-system-v8"
REPO_FULL="${REPO_OWNER}/${REPO_NAME}"

ENVIRONMENT="${1:-all}"

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

################################################################################
# Check Secret Existence (via GitHub CLI)
################################################################################

check_secret_exists() {
  local secret_name="$1"
  local env_name="$2"
  
  if [ -n "$env_name" ]; then
    # Environment secret - check via API
    if gh api "/repos/${REPO_FULL}/environments/${env_name}/secrets" --jq ".secrets[].name" | grep -q "^${secret_name}$"; then
      log_success "Secret '${secret_name}' exists in environment '${env_name}'"
      return 0
    else
      log_error "Secret '${secret_name}' not found in environment '${env_name}'"
      return 1
    fi
  else
    # Repository secret
    if gh secret list | grep -q "^${secret_name}\s"; then
      log_success "Repository secret '${secret_name}' exists"
      return 0
    else
      log_error "Repository secret '${secret_name}' not found"
      return 1
    fi
  fi
}

################################################################################
# Validate Kubeconfig (if available locally)
################################################################################

validate_kubeconfig() {
  local env_name="$1"
  local namespace="overlord-${env_name}"
  
  log_info "Testing Kubernetes access for ${env_name}..."
  
  if kubectl get ns "$namespace" &> /dev/null; then
    log_success "Namespace '${namespace}' accessible"
  else
    log_error "Cannot access namespace '${namespace}'"
    return 1
  fi
  
  # Test service account
  if kubectl get serviceaccount github-actions -n "$namespace" &> /dev/null; then
    log_success "Service account 'github-actions' exists in ${namespace}"
  else
    log_warning "Service account 'github-actions' not found in ${namespace}"
  fi
  
  # Test permissions (try to list pods)
  if kubectl auth can-i list pods -n "$namespace" &> /dev/null; then
    log_success "Service account has 'list pods' permission in ${namespace}"
  else
    log_error "Service account lacks 'list pods' permission in ${namespace}"
    return 1
  fi
  
  return 0
}

################################################################################
# Validate Slack Webhook
################################################################################

validate_slack_webhook() {
  if [ -z "$SLACK_WEBHOOK_URL" ]; then
    log_warning "SLACK_WEBHOOK_URL not set in environment. Cannot test."
    return 1
  fi
  
  log_info "Testing Slack webhook..."
  
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H 'Content-type: application/json' \
    --data '{"text":"🧪 Secrets validation test"}' \
    "$SLACK_WEBHOOK_URL")
  
  if [ "$RESPONSE" = "200" ]; then
    log_success "Slack webhook is functional (HTTP 200)"
    return 0
  else
    log_error "Slack webhook test failed (HTTP $RESPONSE)"
    return 1
  fi
}

################################################################################
# Main Validation Flow
################################################################################

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "              OVERLORD v8.1 - SECRETS VALIDATION"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

VALIDATION_PASS=true

# Check GitHub CLI auth
if ! gh auth status &> /dev/null; then
  log_error "GitHub CLI not authenticated. Run: gh auth login"
  exit 1
fi

log_success "GitHub CLI authenticated"

# Check repository access
if ! gh repo view "$REPO_FULL" &> /dev/null; then
  log_error "Cannot access repository: $REPO_FULL"
  exit 1
fi

log_success "Repository access confirmed"

echo ""
log_info "Checking repository secrets..."
echo ""

# Repository secrets
check_secret_exists "SLACK_WEBHOOK_URL" "" || VALIDATION_PASS=false

if [ "$ENVIRONMENT" = "staging" ] || [ "$ENVIRONMENT" = "all" ]; then
  echo ""
  log_info "Checking staging environment secrets..."
  echo ""
  
  check_secret_exists "KUBECONFIG_STAGING" "staging" || VALIDATION_PASS=false
  
  # Validate Kubernetes access (if kubectl available)
  if command -v kubectl &> /dev/null; then
    validate_kubeconfig "staging" || VALIDATION_PASS=false
  else
    log_warning "kubectl not found. Skipping Kubernetes validation."
  fi
fi

if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "all" ]; then
  echo ""
  log_info "Checking production environment secrets..."
  echo ""
  
  check_secret_exists "KUBECONFIG_PRODUCTION" "production" || VALIDATION_PASS=false
  
  # Validate Kubernetes access (if kubectl available)
  if command -v kubectl &> /dev/null; then
    validate_kubeconfig "production" || VALIDATION_PASS=false
  else
    log_warning "kubectl not found. Skipping Kubernetes validation."
  fi
fi

echo ""
log_info "Testing integrations..."
echo ""

# Test Slack webhook (if available in environment)
validate_slack_webhook || log_warning "Slack webhook validation skipped"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                     VALIDATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if [ "$VALIDATION_PASS" = true ]; then
  log_success "✓ All secrets validated successfully!"
  echo ""
  log_info "Your CI/CD pipeline is ready to use."
  exit 0
else
  log_error "✗ Some validations failed"
  echo ""
  log_info "Fix the issues above and re-run validation."
  exit 1
fi
