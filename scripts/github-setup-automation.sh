#!/usr/bin/env bash

################################################################################
# OVERLORD v8.1 - GitHub Actions Automated Setup Script
################################################################################
# 
# Description: Автоматизированная настройка GitHub Actions CI/CD pipeline
# Version: 1.0.0
# Author: LEGION v8.1 Autonomous Mission Weaver
# Date: 2026-01-07
#
# Usage:
#   ./scripts/github-setup-automation.sh [--dry-run]
#
# Prerequisites:
#   - gh CLI installed and authenticated
#   - kubectl installed with valid kubeconfig
#   - curl for Slack webhook testing
#   - jq for JSON processing
#
################################################################################

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-legion14041981-ui}"
readonly REPO_NAME="${GITHUB_REPOSITORY_NAME:-overlord-trading-system-v8}"
readonly REPO_FULL="${REPO_OWNER}/${REPO_NAME}"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Dry-run mode
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    echo -e "${RED}❌ $*${NC}"
}

log_step() {
    echo -e "\n${CYAN}▶️  $*${NC}"
}

# ============================================================================
# Prerequisites Check
# ============================================================================

check_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v gh &>/dev/null || missing_tools+=("gh")
    command -v kubectl &>/dev/null || missing_tools+=("kubectl")
    command -v curl &>/dev/null || missing_tools+=("curl")
    command -v jq &>/dev/null || missing_tools+=("jq")
    command -v base64 &>/dev/null || missing_tools+=("base64")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install with:"
        echo "  # macOS"
        echo "  brew install gh kubectl curl jq coreutils"
        echo ""
        echo "  # Ubuntu/Debian"
        echo "  sudo apt-get install gh kubectl curl jq coreutils"
        exit 1
    fi
    
    # Check GitHub CLI authentication
    if ! gh auth status &>/dev/null; then
        log_error "GitHub CLI not authenticated"
        log_info "Run: gh auth login"
        exit 1
    fi
    
    # Check repository access
    if ! gh repo view "${REPO_FULL}" &>/dev/null; then
        log_error "Cannot access repository: ${REPO_FULL}"
        log_info "Check repository name and permissions"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# ============================================================================
# Environment Setup
# ============================================================================

create_github_environment() {
    local env_name="$1"
    local wait_timer="${2:-0}"
    local required_reviewers="${3:-}"
    local deployment_branch="${4:-}"
    
    log_step "Creating GitHub Environment: ${env_name}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "[DRY-RUN] Would create environment: ${env_name}"
        log_info "  Wait timer: ${wait_timer} minutes"
        log_info "  Reviewers: ${required_reviewers:-none}"
        log_info "  Branch: ${deployment_branch:-any}"
        return 0
    fi
    
    # Check if environment exists
    if gh api "repos/${REPO_FULL}/environments/${env_name}" &>/dev/null; then
        log_warning "Environment already exists: ${env_name}"
        read -p "Update existing environment? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && return 0
    fi
    
    # Create environment configuration
    local config="{\"wait_timer\": ${wait_timer}, \"prevent_self_review\": true}"
    
    # Add reviewers if specified
    if [[ -n "$required_reviewers" ]]; then
        local reviewers_json="[]"
        IFS=',' read -ra REVIEWERS <<< "$required_reviewers"
        for reviewer in "${REVIEWERS[@]}"; do
            reviewer=$(echo "$reviewer" | xargs) # trim whitespace
            local user_id=$(gh api "users/${reviewer}" --jq '.id')
            reviewers_json=$(echo "$reviewers_json" | jq --argjson id "$user_id" '. += [{"type": "User", "id": $id}]')
        done
        config=$(echo "$config" | jq --argjson reviewers "$reviewers_json" '.reviewers = $reviewers')
    fi
    
    # Add deployment branch if specified
    if [[ -n "$deployment_branch" ]]; then
        config=$(echo "$config" | jq --arg branch "$deployment_branch" \
            '.deployment_branch_policy = {"protected_branches": false, "custom_branch_policies": true}')
    fi
    
    # Create/update environment
    if gh api -X PUT "repos/${REPO_FULL}/environments/${env_name}" \
        --input - <<< "$config" &>/dev/null; then
        log_success "Environment created: ${env_name}"
    else
        log_error "Failed to create environment: ${env_name}"
        return 1
    fi
}

# ============================================================================
# Kubernetes Configuration
# ============================================================================

get_kubeconfig_base64() {
    local context="$1"
    local namespace="$2"
    
    log_step "Generating kubeconfig for context: ${context}"
    
    # Check if context exists
    if ! kubectl config get-contexts -o name | grep -q "^${context}$"; then
        log_error "Kubernetes context not found: ${context}"
        log_info "Available contexts:"
        kubectl config get-contexts -o name | sed 's/^/  /'
        return 1
    fi
    
    # Test connection
    if ! kubectl --context="${context}" -n "${namespace}" get pods &>/dev/null; then
        log_error "Cannot connect to cluster: ${context}"
        log_info "Check your kubeconfig and credentials"
        return 1
    fi
    
    # Generate service account token (Kubernetes 1.24+)
    log_info "Creating service account token..."
    
    local sa_name="github-actions"
    local token
    
    # Create service account if not exists
    kubectl --context="${context}" -n "${namespace}" \
        create serviceaccount "${sa_name}" 2>/dev/null || true
    
    # Create role binding
    kubectl --context="${context}" -n "${namespace}" \
        create rolebinding "${sa_name}-deploy" \
        --clusterrole=edit \
        --serviceaccount="${namespace}:${sa_name}" \
        2>/dev/null || true
    
    # Generate token (valid for 1 year)
    token=$(kubectl --context="${context}" -n "${namespace}" \
        create token "${sa_name}" --duration=8760h)
    
    # Create minimal kubeconfig
    local cluster_url=$(kubectl --context="${context}" config view \
        --minify -o jsonpath='{.clusters[0].cluster.server}')
    local cluster_ca=$(kubectl --context="${context}" config view \
        --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
    
    cat <<EOF | base64 -w 0
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: ${cluster_ca}
    server: ${cluster_url}
  name: ${context}
contexts:
- context:
    cluster: ${context}
    namespace: ${namespace}
    user: ${sa_name}
  name: ${context}
current-context: ${context}
users:
- name: ${sa_name}
  user:
    token: ${token}
EOF
}

# ============================================================================
# Secrets Configuration
# ============================================================================

set_environment_secret() {
    local env_name="$1"
    local secret_name="$2"
    local secret_value="$3"
    
    log_step "Setting environment secret: ${env_name}/${secret_name}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "[DRY-RUN] Would set secret: ${env_name}/${secret_name}"
        log_info "  Value length: ${#secret_value} characters"
        return 0
    fi
    
    # Encrypt secret using repository public key
    local key_id=$(gh api "repos/${REPO_FULL}/environments/${env_name}/secrets/public-key" \
        --jq '.key_id')
    local public_key=$(gh api "repos/${REPO_FULL}/environments/${env_name}/secrets/public-key" \
        --jq '.key')
    
    # Use GitHub CLI to set secret
    echo "$secret_value" | gh secret set "${secret_name}" \
        --repo="${REPO_FULL}" \
        --env="${env_name}" \
        --body=-
    
    if [[ $? -eq 0 ]]; then
        log_success "Secret set: ${secret_name}"
    else
        log_error "Failed to set secret: ${secret_name}"
        return 1
    fi
}

set_repository_secret() {
    local secret_name="$1"
    local secret_value="$2"
    
    log_step "Setting repository secret: ${secret_name}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "[DRY-RUN] Would set repository secret: ${secret_name}"
        log_info "  Value length: ${#secret_value} characters"
        return 0
    fi
    
    echo "$secret_value" | gh secret set "${secret_name}" \
        --repo="${REPO_FULL}" \
        --body=-
    
    if [[ $? -eq 0 ]]; then
        log_success "Secret set: ${secret_name}"
    else
        log_error "Failed to set secret: ${secret_name}"
        return 1
    fi
}

# ============================================================================
# Slack Webhook Configuration
# ============================================================================

test_slack_webhook() {
    local webhook_url="$1"
    
    log_step "Testing Slack webhook..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "[DRY-RUN] Would test Slack webhook"
        return 0
    fi
    
    local payload='{"text":"🚀 OVERLORD CI/CD Setup - Test notification from automated setup script"}'
    
    if curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        --silent \
        --fail \
        "$webhook_url" &>/dev/null; then
        log_success "Slack webhook working"
        return 0
    else
        log_error "Slack webhook test failed"
        return 1
    fi
}

# ============================================================================
# Branch Protection Rules
# ============================================================================

setup_branch_protection() {
    local branch="$1"
    
    log_step "Setting up branch protection: ${branch}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warning "[DRY-RUN] Would set branch protection for: ${branch}"
        return 0
    fi
    
    local protection_config
    
    if [[ "$branch" == "main" ]]; then
        protection_config='{
            "required_status_checks": {
                "strict": true,
                "contexts": [
                    "quality-gates",
                    "security-scanning",
                    "unit-tests",
                    "integration-tests",
                    "e2e-tests",
                    "docker-build"
                ]
            },
            "enforce_admins": false,
            "required_pull_request_reviews": {
                "dismissal_restrictions": {},
                "dismiss_stale_reviews": true,
                "require_code_owner_reviews": false,
                "required_approving_review_count": 1
            },
            "restrictions": null,
            "allow_force_pushes": false,
            "allow_deletions": false,
            "required_conversation_resolution": true
        }'
    else
        # Develop branch - less strict
        protection_config='{
            "required_status_checks": {
                "strict": false,
                "contexts": [
                    "quality-gates",
                    "security-scanning",
                    "unit-tests",
                    "integration-tests"
                ]
            },
            "enforce_admins": false,
            "required_pull_request_reviews": null,
            "restrictions": null,
            "allow_force_pushes": false,
            "allow_deletions": false
        }'
    fi
    
    if gh api -X PUT "repos/${REPO_FULL}/branches/${branch}/protection" \
        --input - <<< "$protection_config" &>/dev/null; then
        log_success "Branch protection enabled: ${branch}"
    else
        log_error "Failed to set branch protection: ${branch}"
        return 1
    fi
}

# ============================================================================
# Interactive Setup
# ============================================================================

interactive_setup() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║        OVERLORD v8.1 - GitHub Actions Setup Wizard         ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "Repository: ${REPO_FULL}"
    log_info "Mode: $([ "$DRY_RUN" == true ] && echo "DRY-RUN (no changes)" || echo "LIVE (will make changes)")"
    echo ""
    
    # Confirm start
    if [[ "$DRY_RUN" == false ]]; then
        read -p "This will modify your GitHub repository. Continue? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
    fi
    
    # === STEP 1: Create Environments ===
    log_step "STEP 1: Creating GitHub Environments"
    echo ""
    
    # Staging environment
    create_github_environment "staging" 0 "" "develop"
    
    # Production environment
    log_info "Enter required reviewers for production (comma-separated GitHub usernames):"
    read -p "Reviewers (default: ${REPO_OWNER}): " reviewers
    reviewers="${reviewers:-${REPO_OWNER}}"
    
    create_github_environment "production" 0 "$reviewers" "main"
    
    # === STEP 2: Configure Kubernetes ===
    log_step "STEP 2: Configuring Kubernetes Credentials"
    echo ""
    
    # Staging kubeconfig
    log_info "Enter Kubernetes context for STAGING:"
    kubectl config get-contexts -o name | sed 's/^/  /'
    read -p "Context: " staging_context
    read -p "Namespace (default: overlord-staging): " staging_namespace
    staging_namespace="${staging_namespace:-overlord-staging}"
    
    staging_kubeconfig=$(get_kubeconfig_base64 "$staging_context" "$staging_namespace")
    set_environment_secret "staging" "KUBECONFIG_STAGING" "$staging_kubeconfig"
    
    # Production kubeconfig
    log_info "Enter Kubernetes context for PRODUCTION:"
    kubectl config get-contexts -o name | sed 's/^/  /'
    read -p "Context: " prod_context
    read -p "Namespace (default: overlord-production): " prod_namespace
    prod_namespace="${prod_namespace:-overlord-production}"
    
    prod_kubeconfig=$(get_kubeconfig_base64 "$prod_context" "$prod_namespace")
    set_environment_secret "production" "KUBECONFIG_PRODUCTION" "$prod_kubeconfig"
    
    # === STEP 3: Configure Slack ===
    log_step "STEP 3: Configuring Slack Notifications"
    echo ""
    
    read -p "Enter Slack webhook URL (or press Enter to skip): " slack_webhook
    
    if [[ -n "$slack_webhook" ]]; then
        test_slack_webhook "$slack_webhook"
        set_repository_secret "SLACK_WEBHOOK_URL" "$slack_webhook"
    else
        log_warning "Skipping Slack configuration"
    fi
    
    # === STEP 4: Optional Secrets ===
    log_step "STEP 4: Configuring Optional Secrets"
    echo ""
    
    # SonarCloud
    read -p "Configure SonarCloud? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter SonarCloud token: " sonar_token
        set_repository_secret "SONAR_TOKEN" "$sonar_token"
    fi
    
    # Codecov
    read -p "Configure Codecov? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter Codecov token: " codecov_token
        set_repository_secret "CODECOV_TOKEN" "$codecov_token"
    fi
    
    # === STEP 5: Branch Protection ===
    log_step "STEP 5: Setting Up Branch Protection Rules"
    echo ""
    
    setup_branch_protection "main"
    setup_branch_protection "develop"
    
    # === STEP 6: Verification ===
    log_step "STEP 6: Verifying Configuration"
    echo ""
    
    verify_setup
}

# ============================================================================
# Verification
# ============================================================================

verify_setup() {
    local errors=0
    
    log_info "Checking environments..."
    for env in staging production; do
        if gh api "repos/${REPO_FULL}/environments/${env}" &>/dev/null; then
            log_success "Environment exists: ${env}"
        else
            log_error "Environment missing: ${env}"
            ((errors++))
        fi
    done
    
    log_info "Checking branch protection..."
    for branch in main develop; do
        if gh api "repos/${REPO_FULL}/branches/${branch}/protection" &>/dev/null; then
            log_success "Branch protected: ${branch}"
        else
            log_error "Branch not protected: ${branch}"
            ((errors++))
        fi
    done
    
    echo ""
    if [[ $errors -eq 0 ]]; then
        log_success "✨ Setup completed successfully!"
        echo ""
        log_info "Next steps:"
        echo "  1. Test workflow: git push origin develop"
        echo "  2. Monitor: https://github.com/${REPO_FULL}/actions"
        echo "  3. Check Slack notifications"
        echo "  4. Review deployment logs"
    else
        log_error "Setup completed with $errors error(s)"
        log_info "Review errors above and re-run script"
        exit 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    check_prerequisites
    interactive_setup
}

# Run
main "$@"
