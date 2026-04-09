#!/bin/bash
###################################################################
# switch-model.sh — Switch active AI provider
#
# Usage:
#   ./scripts/switch-model.sh openai
#   ./scripts/switch-model.sh colab
#   ./scripts/switch-model.sh local
#   ./scripts/switch-model.sh mock
#   ./scripts/switch-model.sh mock-local
#
###################################################################

set -e

PROVIDER=$1
ENV_FILE="$(dirname "$0")/../.env"
ADAPTERS_DIR="$(dirname "$0")/adapters"

# ---- Validate ----
if [ -z "$PROVIDER" ]; then
    echo "Usage: switch-model.sh [openai|colab|local|mock|mock-local]"
    exit 1
fi

# ---- Load current .env ----
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Helpers ----
update_env() {
    local key=$1
    local val=$2
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

set_goose_adapter() {
    update_env "AI_ADAPTER" "goose"
    ln -sf "${ADAPTERS_DIR}/goose.sh" "${ADAPTERS_DIR}/ai.sh"
}

set_mock_adapter() {
    update_env "AI_ADAPTER" "mock"
    ln -sf "${ADAPTERS_DIR}/mock.sh" "${ADAPTERS_DIR}/ai.sh"
}

configure_goose_endpoint() {
    local endpoint=$1
    goose configure provider openai-compatible 2>/dev/null || true
    goose configure base_url "$endpoint" 2>/dev/null || true
}

test_endpoint() {
    local endpoint=$1
    echo ""
    echo "🔍 Testing endpoint..."
    if curl -s --max-time 3 "${endpoint}/models" > /dev/null; then
        echo "✅ Endpoint reachable"
    else
        echo "⚠️  Endpoint not reachable — check server"
    fi
}

echo ""
echo "🔄 Switching provider to: $PROVIDER"

case "$PROVIDER" in

  openai)
    update_env "MODEL_PROVIDER" "openai"
    update_env "MODEL_ENDPOINT" "https://api.openai.com/v1"

    set_goose_adapter
    configure_goose_endpoint "https://api.openai.com/v1"

    echo "✅ Provider:  OpenAI"
    echo "   Endpoint:  https://api.openai.com/v1"
    echo "   Adapter:   goose"

    if [ -z "$OPENAI_API_KEY" ]; then
        echo "⚠️  OPENAI_API_KEY is not set — edit .env before running"
    fi

    test_endpoint "https://api.openai.com/v1"
    ;;

  colab)
    if [ -z "$COLAB_URL" ]; then
        read -rp "📡 Paste your Colab ngrok URL: " COLAB_URL
        if [ -z "$COLAB_URL" ]; then
            echo "❌ COLAB_URL is required for Colab provider"
            exit 1
        fi
    fi

    update_env "MODEL_PROVIDER" "colab"
    update_env "COLAB_URL" "$COLAB_URL"
    update_env "MODEL_ENDPOINT" "${COLAB_URL}/v1"

    set_goose_adapter
    configure_goose_endpoint "${COLAB_URL}/v1"

    echo "✅ Provider:  Colab GPU"
    echo "   Endpoint:  ${COLAB_URL}/v1"
    echo "   Adapter:   goose"

    test_endpoint "${COLAB_URL}/v1"
    ;;

  local)
    LOCAL_ENDPOINT=${MODEL_ENDPOINT:-"http://host.docker.internal:11434/v1"}

    update_env "MODEL_PROVIDER" "local"
    update_env "MODEL_ENDPOINT" "$LOCAL_ENDPOINT"

    set_goose_adapter
    configure_goose_endpoint "$LOCAL_ENDPOINT"

    echo "✅ Provider:  Local Ollama"
    echo "   Endpoint:  $LOCAL_ENDPOINT"
    echo "   Adapter:   goose"

    echo ""
    echo "   Tip: Set MODEL_ENDPOINT in .env to override default"

    test_endpoint "$LOCAL_ENDPOINT"
    ;;

  mock)
    update_env "MODEL_PROVIDER" "mock"
    update_env "MODEL_ENDPOINT" "none"

    set_mock_adapter

    echo "✅ Provider:  Mock (offline mode)"
    echo "   Adapter:   mock"
    echo "   No AI calls will be made"
    ;;

  mock-local)
    update_env "MODEL_PROVIDER" "mock-local"
    update_env "MODEL_ENDPOINT" "http://127.0.0.1:8000/v1"

    set_goose_adapter
    configure_goose_endpoint "http://127.0.0.1:8000/v1"

    echo "✅ Provider:  Mock OpenAI server (local)"
    echo "   Endpoint:  http://127.0.0.1:8000/v1"
    echo "   Adapter:   goose"
    echo ""
    echo "   ⚠️  Start server first: make mock-server"

    test_endpoint "http://127.0.0.1:8000/v1"
    ;;

  *)
    echo "❌ Unknown provider: $PROVIDER"
    echo "   Options: openai | colab | local | mock | mock-local"
    exit 1
    ;;
esac

# ---- Optional Goose config script ----
GOOSE_CONFIG="$(dirname "$0")/../.devcontainer/goose-config.sh"
if [ -f "$GOOSE_CONFIG" ] && [ "$PROVIDER" != "mock" ]; then
    source "$ENV_FILE" 2>/dev/null || true
    bash "$GOOSE_CONFIG"
fi

echo ""
echo "   Run 'make status' to confirm active configuration"
echo ""