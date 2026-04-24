#!/usr/bin/env bash
###################################################################
# health-check.sh — v3.0 (LiteLLM-native)
#
# Goals:
# - Reflect real architecture (LiteLLM + Goose + Mock)
# - Provide accurate signal (not noisy warnings)
# - Be CI-friendly (correct exit codes)
###################################################################

set -euo pipefail

ENV_FILE="$(dirname "$0")/../.env"
QUIET="${1:-}"

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Colors ----
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
RESET='\033[0m'

# ---- Output helpers ----
pass() { [ "$QUIET" != "--quiet" ] && echo -e "${GREEN}✅ $1${RESET}"; }
fail() { echo -e "${RED}❌ $1${RESET}"; }
warn() { [ "$QUIET" != "--quiet" ] && echo -e "${YELLOW}⚠️  $1${RESET}"; }
info() { [ "$QUIET" != "--quiet" ] && echo -e "${CYAN}🔍 $1${RESET}"; }

FAILURES=0

# ---------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------
curl_check() {
    local url="$1"
    local timeout="${2:-5}"

    curl -sS --max-time "$timeout" "$url" 2>/dev/null || return 1
}

check_litellm() {
    local base="$1"
    local root="${base%/v1}"

    # ---- LiteLLM ----
echo ""
info "Checking LiteLLM..."

if [[ "${MODEL_PROVIDER}" == "litellm" || "${AI_ADAPTER}" == "litellm" ]]; then
    BASE="${MODEL_ENDPOINT:-http://litellm:4000/v1}"
    BASE_NO_V1=$(echo "$BASE" | sed 's|/v1$||')

    # Try /health first
    if curl -sf "${BASE_NO_V1}/health" --max-time 3 > /dev/null 2>&1; then
        pass "LiteLLM healthy (/health)"
    
    # Fallback: OpenAI-compatible probe
    elif curl -sf "${BASE}/models" --max-time 3 > /dev/null 2>&1; then
        pass "LiteLLM reachable (/v1/models fallback)"
    
    else
        fail "LiteLLM not reachable (${BASE})"
        FAILURES=$((FAILURES + 1))
    fi
else
    warn "LiteLLM not active (skipping)"
fi
}

check_mock_server() {
    local base="$1"

    info "Checking mock server..."

    if curl_check "$base/health"; then
        pass "Mock server healthy"
    else
        fail "Mock server not reachable ($base/health)"
        FAILURES=$((FAILURES + 1))
    fi
}

# ---------------------------------------------------------------
# Header
# ---------------------------------------------------------------
[ "$QUIET" != "--quiet" ] && {
echo ""
echo -e "${CYAN}🏥 AI Dev Platform — Health Check${RESET}"
echo "=================================="
echo ""
}

# ---------------------------------------------------------------
# Active config
# ---------------------------------------------------------------
info "Active Configuration"
[ "$QUIET" != "--quiet" ] && {
echo "   Provider:  ${MODEL_PROVIDER:-not set}"
echo "   Adapter:   ${AI_ADAPTER:-not set}"
echo "   Endpoint:  ${MODEL_ENDPOINT:-not set}"
echo "   Model:     ${ACTIVE_MODEL:-not set}"
echo "   Project:   ${ACTIVE_PROJECT:-not set}"
echo ""
}

# ---------------------------------------------------------------
# .env
# ---------------------------------------------------------------
info "Checking environment..."

if [ -f "$ENV_FILE" ]; then
    pass ".env file exists"
else
    fail ".env file missing (run: make setup)"
    FAILURES=$((FAILURES + 1))
fi

# ---------------------------------------------------------------
# Goose
# ---------------------------------------------------------------
info "Checking Goose..."

if command -v goose >/dev/null 2>&1; then
    GOOSE_VER=$(goose --version 2>/dev/null || echo "unknown")
    pass "Goose installed ($GOOSE_VER)"
else
    warn "Goose not installed (only needed for agent mode)"
fi

# ---------------------------------------------------------------
# Adapter-specific checks
# ---------------------------------------------------------------
echo ""
info "Checking runtime..."

case "${AI_ADAPTER:-}" in

    mock)
        pass "Mock adapter active (no external dependencies)"
        ;;

    litellm)
        if [ -n "${MODEL_ENDPOINT:-}" ]; then
            check_litellm "$MODEL_ENDPOINT"
        else
            fail "MODEL_ENDPOINT not set for LiteLLM"
            FAILURES=$((FAILURES + 1))
        fi
        ;;

    goose)
        pass "Goose adapter active"

        if [ -n "${MODEL_ENDPOINT:-}" ]; then
            check_litellm "$MODEL_ENDPOINT"
        else
            warn "MODEL_ENDPOINT not set (Goose may fail)"
        fi
        ;;

    *)
        warn "Unknown adapter: ${AI_ADAPTER:-unset}"
        ;;

esac

# ---------------------------------------------------------------
# Optional services
# ---------------------------------------------------------------
echo ""
info "Checking optional services..."

[ -n "${FALLBACK_ENDPOINT:-}" ] && check_mock_server "${FALLBACK_ENDPOINT%/v1}" || \
    info "No fallback endpoint (using mock fallback)"

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
echo ""
echo "=================================="

if [ "$FAILURES" -eq 0 ]; then
    pass "System healthy"
else
    fail "$FAILURES issue(s) detected"
    exit 1
fi

echo ""