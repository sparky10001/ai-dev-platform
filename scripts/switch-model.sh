#!/bin/bash
###################################################################
# switch-model.sh — v6.0 (LiteLLM-first architecture)
#
# Key changes:
# - LiteLLM is the primary gateway for ALL model traffic
# - Goose runs on top of LiteLLM (not OpenAI directly)
# - Removed legacy provider fragmentation
# - Unified fallback model
# - Added resilient curl probing
###################################################################

set -euo pipefail

PROVIDER="${1:-}"
ENV_FILE="$(dirname "$0")/../.env"

# ---------------------------------------------------------------
# Validate input
# ---------------------------------------------------------------
if [ -z "$PROVIDER" ]; then
  echo "Usage: switch-model.sh [litellm|goose|mock|mock-local|colab]"
  exit 1
fi

# ---------------------------------------------------------------
# Ensure .env exists
# ---------------------------------------------------------------
touch "$ENV_FILE"

# ---------------------------------------------------------------
# Load env
# ---------------------------------------------------------------
set -a
source "$ENV_FILE"
set +a

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
update_env() {
  local key="$1"
  local val="$2"

  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

strip_v1() {
  echo "$1" | sed 's|/v1$||'
}

curl_probe() {
  curl -sS \
    --connect-timeout 3 \
    --max-time 5 \
    --retry 2 \
    --retry-delay 1 \
    --retry-connrefused \
    "$1" 2>/dev/null || return 1
}

# ---------------------------------------------------------------
# 🔍 Endpoint Tests
# ---------------------------------------------------------------
test_openai_compatible() {
  local base="$1"
  echo ""
  echo "🔍 Testing OpenAI-compatible endpoint..."

  RESP="$(curl -sS \
    --connect-timeout 3 \
    --max-time 5 \
    "${base}/models" || true)"

  if echo "$RESP" | jq -e '.data' >/dev/null 2>&1; then
    echo "✅ OpenAI-compatible endpoint reachable"
    return 0
  fi

  if echo "$RESP" | jq -e '.error' >/dev/null 2>&1; then
    echo "⚠️  Endpoint requires auth (still valid)"
    return 0
  fi

  echo "❌ Endpoint not OpenAI-compatible"
  return 1
}

# ---------------------------------------------------------------
# Start
# ---------------------------------------------------------------
echo ""
echo "🔄 Switching provider to: $PROVIDER"

# ---------------------------------------------------------------
# Provider Switch
# ---------------------------------------------------------------
case "$PROVIDER" in

# ---------------------------------------------------------------
# ⚡ LiteLLM (PRIMARY PATH)
# ---------------------------------------------------------------
litellm)
  BASE="${LITELLM_BASE_URL:-http://litellm:4000/v1}"
  MODEL="${LITELLM_MODEL:-fast}"
  KEY="${LITELLM_MASTER_KEY:-ai-dev-platform}"

  update_env "MODEL_PROVIDER"       "litellm"
  update_env "MODEL_ENDPOINT"       "$BASE"
  update_env "AI_ADAPTER"           "litellm"
  update_env "LITELLM_MODEL"        "$MODEL"
  update_env "LITELLM_MASTER_KEY"   "$KEY"
  update_env "FALLBACK_CHAIN"       "litellm,mock"

  echo "✅ Provider: LiteLLM (unified gateway)"
  echo "   Adapter:  litellm"
  echo "   Endpoint: $BASE"
  echo "   Model:    $MODEL"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# 🦆 Goose (Agent runtime on LiteLLM)
# ---------------------------------------------------------------
goose)
  BASE="${LITELLM_BASE_URL:-http://litellm:4000/v1}"

  update_env "MODEL_PROVIDER"   "litellm"
  update_env "MODEL_ENDPOINT"   "$BASE"
  update_env "AI_ADAPTER"       "goose"
  update_env "GOOSE_PROVIDER"   "litellm"
  update_env "GOOSE_MODEL"      "${GOOSE_MODEL:-fast}"
  update_env "FALLBACK_CHAIN"   "litellm,mock"

  echo "✅ Mode:     Goose (agent runtime)"
  echo "   Backend:  LiteLLM"
  echo "   Endpoint: $BASE"
  echo "   Model:    ${GOOSE_MODEL:-fast}"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# ☁️ Colab (still supported as external)
# ---------------------------------------------------------------
colab)
  if [ -z "${COLAB_URL:-}" ]; then
    echo "❌ COLAB_URL not set — run: ./scripts/start-colab-proxy.sh"
    exit 1
  fi

  BASE="${COLAB_URL}/v1"

  update_env "MODEL_PROVIDER"  "colab"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "litellm"
  update_env "FALLBACK_CHAIN"  "litellm,mock"

  echo "✅ Colab (via LiteLLM-compatible API)"
  echo "   Endpoint: $BASE"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# 🧪 Mock (offline)
# ---------------------------------------------------------------
mock)
  update_env "MODEL_PROVIDER"  "mock"
  update_env "MODEL_ENDPOINT"  "none"
  update_env "AI_ADAPTER"      "mock"
  update_env "FALLBACK_CHAIN"  "mock"

  echo "✅ Mock (offline mode)"
  ;;

# ---------------------------------------------------------------
# 🧪 Mock-local (OpenAI-compatible test server)
# ---------------------------------------------------------------
mock-local)
  BASE="http://127.0.0.1:8000/v1"

  update_env "MODEL_PROVIDER"  "mock-local"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "litellm"
  update_env "FALLBACK_CHAIN"  "litellm,mock"

  echo "✅ Mock OpenAI-compatible server"
  echo "   Endpoint: $BASE"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# ❌ Unknown
# ---------------------------------------------------------------
*)
  echo "❌ Unknown provider: $PROVIDER"
  echo "   Options: litellm | goose | colab | mock | mock-local"
  exit 1
  ;;
esac

echo ""
echo "   Run 'make status' to confirm configuration"
echo ""