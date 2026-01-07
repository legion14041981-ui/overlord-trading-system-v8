#!/bin/bash
# ==============================================================================
# Overlord v8.1 - Smoke Tests for Production
# ==============================================================================
# Description: Quick validation of critical system functionality
# Usage: ./smoke-tests.sh [environment]
# Exit Codes: 0 (all tests passed), 1 (one or more tests failed)
# ==============================================================================

set -euo pipefail

# Configuration
ENVIRONMENT=${1:-production}

case $ENVIRONMENT in
    production)
        BASE_URL="https://overlord.example.com"
        ;;
    staging)
        BASE_URL="https://staging.overlord.example.com"
        ;;
    *)
        echo "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0

# Helper functions
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

test_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# ==============================================================================
# Test Suite
# ==============================================================================
echo -e "${BLUE}\n========================================${NC}"
echo -e "${BLUE}Overlord v8.1 - Smoke Tests${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Base URL: ${BASE_URL}${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ==============================================================================
# Test 1: Basic Health Check
# ==============================================================================
test_info "Test 1: Basic Health Check"
if curl -sf "${BASE_URL}/health" | grep -q "healthy"; then
    test_pass "Health endpoint returns healthy status"
else
    test_fail "Health endpoint check failed"
fi

# ==============================================================================
# Test 2: Readiness Probe
# ==============================================================================
test_info "Test 2: Readiness Probe"
if curl -sf "${BASE_URL}/health/ready" > /dev/null; then
    test_pass "Readiness probe successful"
else
    test_fail "Readiness probe failed"
fi

# ==============================================================================
# Test 3: Liveness Probe
# ==============================================================================
test_info "Test 3: Liveness Probe"
if curl -sf "${BASE_URL}/health/live" > /dev/null; then
    test_pass "Liveness probe successful"
else
    test_fail "Liveness probe failed"
fi

# ==============================================================================
# Test 4: API Documentation
# ==============================================================================
test_info "Test 4: API Documentation"
if curl -sf "${BASE_URL}/docs" > /dev/null; then
    test_pass "API documentation is accessible"
else
    test_fail "API documentation is not accessible"
fi

# ==============================================================================
# Test 5: Metrics Endpoint
# ==============================================================================
test_info "Test 5: Metrics Endpoint"
if curl -sf "${BASE_URL}/metrics" > /dev/null; then
    test_pass "Metrics endpoint is accessible"
else
    test_fail "Metrics endpoint check failed"
fi

# ==============================================================================
# Test 6: API Version
# ==============================================================================
test_info "Test 6: API Version Check"
VERSION=$(curl -sf "${BASE_URL}/api/v1/version" | jq -r '.version' 2>/dev/null || echo "unknown")
if [ "$VERSION" != "unknown" ]; then
    test_pass "API version: $VERSION"
else
    test_fail "Could not retrieve API version"
fi

# ==============================================================================
# Test 7: Authentication Required
# ==============================================================================
test_info "Test 7: Authentication Check"
STATUS_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/portfolio" || echo "000")
if [ "$STATUS_CODE" == "401" ] || [ "$STATUS_CODE" == "403" ]; then
    test_pass "Authentication correctly required (HTTP $STATUS_CODE)"
else
    test_fail "Authentication check failed (HTTP $STATUS_CODE)"
fi

# ==============================================================================
# Test 8: Database Connectivity
# ==============================================================================
test_info "Test 8: Database Health"
if curl -sf "${BASE_URL}/health" | jq -e '.checks.database == "ok"' > /dev/null 2>&1; then
    test_pass "Database is connected and healthy"
else
    test_fail "Database connectivity issue detected"
fi

# ==============================================================================
# Test 9: Response Time Check
# ==============================================================================
test_info "Test 9: Response Time Benchmark"
RESPONSE_TIME=$(curl -sf -o /dev/null -w "%{time_total}" "${BASE_URL}/health" || echo "999")
RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc)
if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
    test_pass "Response time: ${RESPONSE_MS} ms (< 1000ms)"
else
    test_fail "Response time too slow: ${RESPONSE_MS} ms"
fi

# ==============================================================================
# Test 10: Trading System Status
# ==============================================================================
test_info "Test 10: Trading System Status"
if curl -sf "${BASE_URL}/api/v1/status" | jq -e '.trading_enabled == true' > /dev/null 2>&1; then
    test_pass "Trading system is enabled and running"
else
    test_fail "Trading system status check failed"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Smoke Test Results${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️ $FAILED test(s) failed${NC}"
    exit 1
fi
