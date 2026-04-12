#!/bin/bash
###################################################################
# health-check.sh — Check health of all platform components
#
# Usage:
#   ./scripts/health-check.sh
#   ./scripts/health-check.sh --quiet
###################################################################

ENV_FILE="$(dirname "$0")/../.env"
QUIET=${1:-""}

# ---- Load .env ----
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Colors ----
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
RESET='\033[0m'

pass() { echo -e "${GREEN}✅ $1${RESET}"; }
fail() { echo -e "${RED}❌ $1${RESET}"; }
warn() { echo -e "${YELLOW}⚠️  $1${RESET}"; }
info() { echo -e "${CYAN}🔍 $1${RESET}"; }

FAILURES=0

check_url() {
    local name=$1
    local url=$2
    local timeout=${3:-5}

    if curl -sf "$url" --max-time "$timeout" > /dev/null 2>&1; then
        pass "$name — reachable ($url)"
    else
        fail "$name — not reachable ($url)"
        FAILURES=$((FAILURES + 1))
    fi
}

echo ""
echo -e "${CYAN}🏥 AI Dev Platform — Health Check${RESET}"
echo "=================================="
echo ""

# ---- Active Configuration ----
info "Active Configuration"
echo "   Provider:  ${MODEL_PROVIDER:-not set}"
echo "   Endpoint:  ${MODEL_ENDPOINT:-not set}"
echo "   Adapter:   ${AI_ADAPTER:-not set}"
echo "   Project:   ${ACTIVE_PROJECT:-not set}"
echo ""

# ---- Adapter symlink ----
info "Checking adapter..."
ADAPTER="${AI_ADAPTER:-goose}"
echo "Adapter: $ADAPTER"
if [ -L "$ADAPTER_LINK" ]; then
    TARGET=$(readlink "$ADAPTER_LINK")
    pass "Adapter symlink → $TARGET"
else
    fail "Adapter symlink not set — run: make openai|colab|local|mock"
    FAILURES=$((FAILURES + 1))
fi

# ---- Goose ----
echo ""
info "Checking Goose..."
if command -v goose &> /dev/null; then
    GOOSE_VER=$(goose --version 2>/dev/null || echo "unknown")
    pass "Goose installed ($GOOSE_VER)"
else
    warn "Goose not installed — adapter will fall back to mock"
fi

# ---- Model endpoint ----
echo ""
info "Checking model endpoint..."
if [ -z "$MODEL_ENDPOINT" ] || [ "$MODEL_ENDPOINT" = "none" ]; then
    if [ "$MODEL_PROVIDER" = "mock" ]; then
        pass "Mock mode — no endpoint needed"
    else
        warn "MODEL_ENDPOINT not set"
    fi
else
    check_url "Model endpoint" "$MODEL_ENDPOINT"
fi

# ---- Managed projects ----
echo ""
info "Checking managed projects..."

check_project() {
    local name=$1
    local url=$2
    if [ -n "$url" ]; then
        check_url "$name" "$url"
    else
        warn "$name — URL not configured"
    fi
}

check_project "private-ai-stack (Kong)"  "${PRIVATE_AI_STACK_URL:-}"
check_project "agent-sim (env server)"   "${AGENT_SIM_URL:-}"
check_project "arb-agent-system"         "${ARB_AGENT_URL:-}"

# ---- Environment variables ----
echo ""
info "Checking environment..."

if [ -f "$ENV_FILE" ]; then
    pass ".env file exists"
else
    fail ".env file missing — run: make setup"
    FAILURES=$((FAILURES + 1))
fi

if [ "$MODEL_PROVIDER" = "openai" ] && [ -z "$OPENAI_API_KEY" ]; then
    warn "OPENAI_API_KEY not set (required for OpenAI provider)"
fi

if [ "$MODEL_PROVIDER" = "colab" ] && [ -z "$COLAB_URL" ]; then
    fail "COLAB_URL not set (required for Colab provider)"
    FAILURES=$((FAILURES + 1))
fi

# ---- Summary ----
echo ""
echo "=================================="
if [ "$FAILURES" -eq 0 ]; then
    pass "All checks passed!"
else
    fail "$FAILURES check(s) failed"
    exit 1
fi
echo ""
