#!/bin/bash
###################################################################
# switch-model.sh — Switch active AI provider (v3 hardened)
#
# Design:
#   - Explicit provider ↔ adapter mapping
#   - Centralized endpoint testing
#   - No hidden coupling
#   - Deterministic .env updates
###################################################################

set -euo pipefail

PROVIDER=${1:-}
ENV_FILE="$(dirname "$0")/../.env"

# ---- Validate ----
if [ -z "$PROVIDER" ]; then
    echo "Usage: switch-model.sh [openai|openai-goose|http|colab|local|mock|mock-local]"
    exit 1
fi

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ---- Helpers ----
update_env() {
    local key="$1"
    local val="$2"

    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

test_endpoint() {
    local endpoint="$1"

    echo ""
    echo "🔍 Testing endpoint..."

    if curl -s --max-time 3 "${endpoint}/models" > /dev/null 2>&1; then
        echo "✅ Endpoint reachable"
    else
        echo "⚠️  Endpoint not reachable — check server"
    fi
}

echo ""
echo "🔄 Switching provider to: $PROVIDER"

# ---- Defaults (used for centralized testing) ----
SHOULD_TEST_ENDPOINT=true
ENDPOINT_TO_TEST=""

case "$PROVIDER" in

# ---------------------------------------------------------------
# 🌐 OpenAI (Direct Adapter)
# ---------------------------------------------------------------
openai)
    update_env "MODEL_PROVIDER" "openai"
    update_env "MODEL_ENDPOINT" "https://api.openai.com/v1"
    update_env "AI_ADAPTER" "openai"

    echo "✅ Provider:  OpenAI"
    echo "   Endpoint:  https://api.openai.com/v1"
    echo "   Adapter:   openai"

    SHOULD_TEST_ENDPOINT=false

    if [ -z "${OPENAI_API_KEY:-}" ]; then
        echo ""
        echo "⚠️  OPENAI_API_KEY is not set"
        echo "   Edit .env before running"
    fi
    ;;

# ---------------------------------------------------------------
# 🦆 OpenAI via Goose (Agent Mode)
# ---------------------------------------------------------------
openai-goose)
    update_env "MODEL_PROVIDER" "openai"
    update_env "MODEL_ENDPOINT" "https://api.openai.com/v1"
    update_env "AI_ADAPTER" "goose"

    echo "✅ Provider:  OpenAI"
    echo "   Endpoint:  https://api.openai.com/v1"
    echo "   Adapter:   goose (agent mode)"

    SHOULD_TEST_ENDPOINT=false
    ;;

# ---------------------------------------------------------------
# 🔗 HTTP (universal adapter)
# ---------------------------------------------------------------
http)
    if [ -z "${MODEL_ENDPOINT:-}" ] || [ "$MODEL_ENDPOINT" = "none" ]; then
        MODEL_ENDPOINT="http://127.0.0.1:8000/v1"
    fi

    update_env "MODEL_PROVIDER" "http"
    update_env "MODEL_ENDPOINT" "$MODEL_ENDPOINT"
    update_env "AI_ADAPTER" "http-agent"

    echo "✅ Adapter: http-agent (dependency-free)"
    echo "   Endpoint: $MODEL_ENDPOINT"

    ENDPOINT_TO_TEST="$MODEL_ENDPOINT"
    ;;

# ---------------------------------------------------------------
# 🖥️ Local (Ollama / private stack)
# ---------------------------------------------------------------
local)
    LOCAL_ENDPOINT="${MODEL_ENDPOINT:-http://host.docker.internal:11434/v1}"

    update_env "MODEL_PROVIDER" "local"
    update_env "MODEL_ENDPOINT" "$LOCAL_ENDPOINT"
    update_env "AI_ADAPTER" "http-agent"

    echo "✅ Provider:  Local model"
    echo "   Endpoint:  $LOCAL_ENDPOINT"
    echo "   Adapter:   http-agent"

    echo ""
    echo "   Tip: Override MODEL_ENDPOINT in .env if needed"

    ENDPOINT_TO_TEST="$LOCAL_ENDPOINT"
    ;;

# ---------------------------------------------------------------
# ☁️ Colab proxy
# ---------------------------------------------------------------
colab)
    if [ -z "${COLAB_URL:-}" ]; then
        echo "❌ COLAB_URL not set"
        echo "   Set it in .env or export before running"
        exit 1
    fi

    ENDPOINT="${COLAB_URL}/v1"

    update_env "MODEL_PROVIDER" "colab"
    update_env "MODEL_ENDPOINT" "$ENDPOINT"
    update_env "AI_ADAPTER" "http-agent"

    echo "✅ Provider:  Colab GPU"
    echo "   Endpoint:  $ENDPOINT"
    echo "   Adapter:   http-agent"

    ENDPOINT_TO_TEST="$ENDPOINT"
    ;;

# ---------------------------------------------------------------
# 🧪 Mock (offline)
# ---------------------------------------------------------------
mock)
    update_env "MODEL_PROVIDER" "mock"
    update_env "MODEL_ENDPOINT" "none"
    update_env "AI_ADAPTER" "mock"

    echo "✅ Provider:  Mock (offline)"
    echo "   Adapter:   mock"
    echo "   No network calls"

    SHOULD_TEST_ENDPOINT=false
    ;;

# ---------------------------------------------------------------
# 🧪 Mock-local (OpenAI-compatible server)
# ---------------------------------------------------------------
mock-local)
    ENDPOINT="http://127.0.0.1:8000/v1"

    update_env "MODEL_PROVIDER" "mock-local"
    update_env "MODEL_ENDPOINT" "$ENDPOINT"
    update_env "AI_ADAPTER" "http-agent"

    echo "✅ Provider:  Mock OpenAI server"
    echo "   Endpoint:  $ENDPOINT"
    echo "   Adapter:   http-agent"

    echo ""
    echo "   ⚠️  Start server first: make mock-server"

    ENDPOINT_TO_TEST="$ENDPOINT"
    ;;

# ---------------------------------------------------------------
# ❌ Unknown
# ---------------------------------------------------------------
*)
    echo "❌ Unknown provider: $PROVIDER"
    echo "   Options: openai | openai-goose | http | colab | local | mock | mock-local"
    exit 1
    ;;

esac

# ---------------------------------------------------------------
# 🔍 Centralized Endpoint Test
# ---------------------------------------------------------------
if [ "$SHOULD_TEST_ENDPOINT" = true ] && [ -n "$ENDPOINT_TO_TEST" ]; then
    test_endpoint "$ENDPOINT_TO_TEST"
fi

echo ""
echo "   Run 'make status' to confirm configuration"
echo ""