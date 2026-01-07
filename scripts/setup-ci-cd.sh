#!/bin/bash

################################################################################
# Overlord v8.1 - CI/CD Setup Automation Script
################################################################################
# 
# This script automates the setup and validation of GitHub Actions CI/CD
# pipeline for Overlord Trading System.
# 
# Prerequisites:
# - GitHub CLI (gh) installed and authenticated
# - kubectl installed with valid cluster access
# - curl for API testing
# 
# Usage:
#   ./scripts/setup-ci-cd.sh [--dry-run] [--skip-secrets] [--skip-k8s]
# 
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="legion14041981-ui"
REPO_NAME="overlord-trading-system-v8"
REPO_FULL="${REPO_OWNER}/${REPO_NAME}"

# Parse arguments
DRY_RUN=false
SKIP_SECRETS=false
SKIP_K8S=false

for arg in "$@"; do
  case $arg in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-secrets)
      SKIP_SECRETS=true
      shift
      ;;
    --skip-k8s)
      SKIP_K8S=true
      shift
      ;;
    --help)
      echo "Usage: $0 [--dry-run] [--skip-secrets] [--skip-k8s]"
      echo ""
      echo "Options:"
      echo "  --dry-run       Run checks without making changes"
      echo "  --skip-secrets  Skip secret configuration (use for re-validation)"
      echo "  --skip-k8s      Skip Kubernetes validation"
      echo "  --help          Show this help message"
      exit 0
      ;;
  esac
done

################################################################################
# Helper Functions
################################################################################

log_info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
  echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
  echo -e "${RED}✗${NC} $1"
}

log_header() {
  echo ""
  echo "═══════════════════════════════════════════════════════════════════"
  echo "  $1"
  echo "═══════════════════════════════════════════════════════════════════"
  echo ""
}

check_command() {
  if command -v "$1" &> /dev/null; then
    log_success "$1 is installed"
    return 0
  else
    log_error "$1 is not installed"
    return 1
  fi
}

################################################################################
# Step 1: Check Prerequisites
################################################################################

log_header "Step 1: Checking Prerequisites"

log_info "Checking required tools..."

PREREQ_OK=true

if ! check_command "gh"; then
  log_error "GitHub CLI is required. Install: https://cli.github.com/"
  PREREQ_OK=false
fi

if ! check_command "kubectl"; then
  log_warning "kubectl not found. Kubernetes validation will be skipped."
  SKIP_K8S=true
fi

if ! check_command "curl"; then
  log_error "curl is required for API testing"
  PREREQ_OK=false
fi

if ! check_command "jq"; then
  log_warning "jq not found. JSON parsing will be limited."
fi

if [ "$PREREQ_OK" = false ]; then
  log_error "Prerequisites not met. Please install missing tools."
  exit 1
fi

log_success "All prerequisites satisfied"

################################################################################
# Step 2: Authenticate GitHub CLI
################################################################################

log_header "Step 2: GitHub Authentication"

if gh auth status &> /dev/null; then
  log_success "GitHub CLI is authenticated"
  GITHUB_USER=$(gh api user --jq '.login')
  log_info "Authenticated as: ${GITHUB_USER}"
else
  log_error "GitHub CLI not authenticated"
  log_info "Run: gh auth login"
  exit 1
fi

# Check repository access
if gh repo view "$REPO_FULL" &> /dev/null; then
  log_success "Repository access confirmed: $REPO_FULL"
else
  log_error "Cannot access repository: $REPO_FULL"
  log_info "Ensure you have admin access to the repository"
  exit 1
fi

################################################################################
# Step 3: Create GitHub Environments
################################################################################

log_header "Step 3: Creating GitHub Environments"

if [ "$DRY_RUN" = true ]; then
  log_warning "DRY RUN: Skipping environment creation"
else
  log_info "Creating 'staging' environment..."
  
  # Note: GitHub CLI doesn't directly support environment creation
  # Users must create environments via web UI
  
  log_warning "GitHub Environments must be created manually via web UI:"
  log_info "1. Go to: https://github.com/${REPO_FULL}/settings/environments"
  log_info "2. Click 'New environment'"
  log_info "3. Create 'staging' environment (no protection rules)"
  log_info "4. Create 'production' environment with:"
  log_info "   - Required reviewers: ${GITHUB_USER}"
  log_info "   - Deployment branches: main only"
  
  read -p "Press Enter after creating environments..."
fi

################################################################################
# Step 4: Validate Kubernetes Access
################################################################################

if [ "$SKIP_K8S" = false ]; then
  log_header "Step 4: Kubernetes Cluster Validation"
  
  log_info "Checking Kubernetes cluster access..."
  
  # Check staging cluster
  if kubectl get ns overlord-staging &> /dev/null; then
    log_success "Staging namespace exists: overlord-staging"
  else
    log_warning "Staging namespace not found. Creating..."
    if [ "$DRY_RUN" = false ]; then
      kubectl create namespace overlord-staging || log_warning "Failed to create namespace"
    fi
  fi
  
  # Check production cluster
  if kubectl get ns overlord-production &> /dev/null; then
    log_success "Production namespace exists: overlord-production"
  else
    log_warning "Production namespace not found. Creating..."
    if [ "$DRY_RUN" = false ]; then
      kubectl create namespace overlord-production || log_warning "Failed to create namespace"
    fi
  fi
  
  # Create service accounts
  log_info "Creating GitHub Actions service accounts..."
  
  for NS in "overlord-staging" "overlord-production"; do
    if kubectl get serviceaccount github-actions -n "$NS" &> /dev/null; then
      log_success "Service account exists in $NS"
    else
      if [ "$DRY_RUN" = false ]; then
        log_info "Creating service account in $NS..."
        kubectl create serviceaccount github-actions -n "$NS"
        kubectl create rolebinding github-actions-deploy \
          --clusterrole=edit \
          --serviceaccount="$NS:github-actions" \
          --namespace="$NS"
        log_success "Service account created in $NS"
      fi
    fi
  done
  
  log_success "Kubernetes validation complete"
else
  log_warning "Kubernetes validation skipped"
fi

################################################################################
# Step 5: Generate Kubeconfig Secrets
################################################################################

if [ "$SKIP_K8S" = false ] && [ "$SKIP_SECRETS" = false ]; then
  log_header "Step 5: Generating Kubeconfig Secrets"
  
  log_info "Generating kubeconfig for staging..."
  
  STAGING_TOKEN=$(kubectl create token github-actions -n overlord-staging --duration=8760h 2>/dev/null || echo "")
  
  if [ -n "$STAGING_TOKEN" ]; then
    log_success "Staging token generated"
    
    # Save to temp file for manual upload
    echo "$STAGING_TOKEN" | base64 -w 0 > /tmp/kubeconfig_staging_token.b64
    log_info "Staging token saved to: /tmp/kubeconfig_staging_token.b64"
  else
    log_warning "Failed to generate staging token. You may need to generate manually."
  fi
  
  log_info "Generating kubeconfig for production..."
  
  PRODUCTION_TOKEN=$(kubectl create token github-actions -n overlord-production --duration=8760h 2>/dev/null || echo "")
  
  if [ -n "$PRODUCTION_TOKEN" ]; then
    log_success "Production token generated"
    
    echo "$PRODUCTION_TOKEN" | base64 -w 0 > /tmp/kubeconfig_production_token.b64
    log_info "Production token saved to: /tmp/kubeconfig_production_token.b64"
  else
    log_warning "Failed to generate production token. You may need to generate manually."
  fi
  
  log_warning "\nIMPORTANT: Add these secrets to GitHub:"
  log_info "1. Go to: https://github.com/${REPO_FULL}/settings/secrets/actions"
  log_info "2. Add environment secret 'KUBECONFIG_STAGING' to 'staging' environment"
  log_info "3. Add environment secret 'KUBECONFIG_PRODUCTION' to 'production' environment"
  log_info "4. Paste the base64-encoded tokens from /tmp/kubeconfig_*_token.b64"
  
  read -p "Press Enter after adding Kubernetes secrets..."
fi

################################################################################
# Step 6: Configure Slack Notifications
################################################################################

log_header "Step 6: Slack Webhook Configuration"

log_info "Testing Slack webhook (if configured)..."

if [ -n "$SLACK_WEBHOOK_URL" ]; then
  log_info "Slack webhook URL found in environment"
  
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H 'Content-type: application/json' \
    --data '{"text":"🤖 CI/CD Setup Test from OVERLORD v8.1"}' \
    "$SLACK_WEBHOOK_URL")
  
  if [ "$RESPONSE" = "200" ]; then
    log_success "Slack webhook is working!"
  else
    log_error "Slack webhook test failed (HTTP $RESPONSE)"
  fi
else
  log_warning "SLACK_WEBHOOK_URL not set. Skipping test."
  log_info "To configure:"
  log_info "1. Create webhook at: https://api.slack.com/messaging/webhooks"
  log_info "2. Add as repository secret: SLACK_WEBHOOK_URL"
  log_info "3. Visit: https://github.com/${REPO_FULL}/settings/secrets/actions"
fi

################################################################################
# Step 7: Setup Branch Protection
################################################################################

log_header "Step 7: Branch Protection Configuration"

if [ "$DRY_RUN" = true ]; then
  log_warning "DRY RUN: Skipping branch protection setup"
else
  log_info "Configuring branch protection for 'main'..."
  
  # Note: Branch protection requires admin access and is complex via API
  log_warning "Branch protection must be configured manually:"
  log_info "1. Go to: https://github.com/${REPO_FULL}/settings/branches"
  log_info "2. Add rule for branch: main"
  log_info "3. Enable:"
  log_info "   ✓ Require a pull request before merging"
  log_info "   ✓ Require status checks to pass"
  log_info "   ✓ Require conversation resolution"
  log_info "   ✗ Do not allow force pushes"
  log_info "   ✗ Do not allow deletions"
  
  read -p "Press Enter after configuring branch protection..."
fi

################################################################################
# Step 8: Test CI/CD Pipeline
################################################################################

log_header "Step 8: CI/CD Pipeline Test"

log_info "Creating test branch to trigger pipeline..."

if [ "$DRY_RUN" = false ]; then
  TEST_BRANCH="test/ci-cd-setup-$(date +%s)"
  
  log_info "Creating branch: $TEST_BRANCH"
  
  git checkout -b "$TEST_BRANCH" 2>/dev/null || log_warning "Branch already exists or git error"
  
  # Make a trivial change
  echo "# CI/CD Setup Test - $(date)" >> README.md
  git add README.md
  git commit -m "test: Verify CI/CD pipeline setup"
  
  log_info "Pushing test branch..."
  git push origin "$TEST_BRANCH"
  
  log_success "Test branch pushed: $TEST_BRANCH"
  log_info "Monitor workflow at: https://github.com/${REPO_FULL}/actions"
  
  log_warning "\nTo complete test:"
  log_info "1. Wait for workflow to complete"
  log_info "2. Verify all jobs pass"
  log_info "3. Check Docker image in ghcr.io"
  log_info "4. Delete test branch: git branch -D $TEST_BRANCH && git push origin --delete $TEST_BRANCH"
else
  log_warning "DRY RUN: Skipping pipeline test"
fi

################################################################################
# Step 9: Validation Report
################################################################################

log_header "Step 9: Setup Validation Report"

log_info "Running final validation checks..."

VALIDATION_PASS=true

# Check GitHub repository
if gh repo view "$REPO_FULL" &> /dev/null; then
  log_success "✓ Repository accessible"
else
  log_error "✗ Repository access failed"
  VALIDATION_PASS=false
fi

# Check workflows exist
if [ -f ".github/workflows/ci-cd-full-cycle.yml" ]; then
  log_success "✓ CI/CD workflow file exists"
else
  log_error "✗ CI/CD workflow file missing"
  VALIDATION_PASS=false
fi

# Check scripts exist
if [ -f "scripts/pre-deployment-checks.sh" ] && [ -f "scripts/smoke-tests.sh" ]; then
  log_success "✓ Deployment scripts exist"
else
  log_error "✗ Deployment scripts missing"
  VALIDATION_PASS=false
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    SETUP VALIDATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if [ "$VALIDATION_PASS" = true ]; then
  log_success "✓ All validation checks passed!"
  echo ""
  log_info "Next steps:"
  echo "  1. Add GitHub Secrets (if not done):"
  echo "     - KUBECONFIG_STAGING (environment secret)"
  echo "     - KUBECONFIG_PRODUCTION (environment secret)"
  echo "     - SLACK_WEBHOOK_URL (repository secret)"
  echo ""
  echo "  2. Create GitHub Environments (if not done):"
  echo "     - staging (no protection)"
  echo "     - production (with required reviewers)"
  echo ""
  echo "  3. Configure branch protection for 'main'"
  echo ""
  echo "  4. Test full pipeline:"
  echo "     - Push to develop → auto-deploy to staging"
  echo "     - Push to main → approval gate → deploy to production"
  echo ""
  log_success "CI/CD setup is ready for production! 🚀"
else
  log_error "✗ Some validation checks failed"
  log_info "Review errors above and re-run script"
  exit 1
fi

echo ""
