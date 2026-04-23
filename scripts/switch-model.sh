#!/bin/bash
###################################################################
# switch-model.sh — v5.2 (Production Hardened)
#
# Fixes from v5.1:
# - Renamed AI_FALLBACK_CHAIN → FALLBACK_CHAIN for consistency
#   with router.sh and _base.sh (both read FALLBACK_CHAIN)
# - No symlinks anywhere
###################################################################

set -euo pipefail

PROVIDER="${1:-}"
ENV_FILE="$(dirname "$0")/../.env"

# ---------------------------------------------------------------
# Validate input
# ---------------------------------------------------------------
if [ -z "$PROVIDER" ]; then
  echo "Usage: switch-model.sh [openai|openai-goose|http|colab|ollama|local|mock|mock-local]"
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
  curl -sS -f --max-time 3 "$1" 2>/dev/null || return 1
}

# ---------------------------------------------------------------
# 🔍 Endpoint Tests
# ---------------------------------------------------------------

test_ollama() {
  local base="$1"
  echo ""
  echo "🔍 Testing Ollama endpoint..."

  if curl_probe "${base}/api/tags" | jq -e '.models' >/dev/null 2>&1; then
    echo "✅ Ollama reachable"
    return 0
  fi

  echo "❌ Ollama not reachable (run: ollama serve or make up in ollama-service/)"
  return 1
}

test_openai() {
  local base="$1"
  echo ""
  echo "🔍 Testing OpenAI endpoint..."

  RESP="$(curl -sS --max-time 3 "${base}/models" || true)"

  if echo "$RESP" | jq -e '.error.type' >/dev/null 2>&1; then
    echo "✅ OpenAI endpoint reachable (auth required)"
    return 0
  fi

  echo "⚠️  Unable to verify OpenAI endpoint (check API key/network)"
  return 0
}

test_openai_compatible() {
  local base="$1"
  echo ""
  echo "🔍 Testing OpenAI-compatible endpoint..."

  RESP="$(curl -sS --max-time 3 "${base}/models" || true)"

  if echo "$RESP" | jq -e '.data' >/dev/null 2>&1; then
    echo "✅ OpenAI-compatible endpoint reachable"
    return 0
  fi

  if echo "$RESP" | jq -e '.error' >/dev/null 2>&1; then
    echo "⚠️  Endpoint requires auth (looks OpenAI-compatible)"
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
# 🌐 OpenAI
# ---------------------------------------------------------------
openai)
  BASE="https://api.openai.com/v1"

  update_env "MODEL_PROVIDER"  "openai"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "openai"
  update_env "FALLBACK_CHAIN"  "openai,mock"

  echo "✅ Provider: OpenAI"
  echo "   Endpoint: $BASE"
  echo "   Adapter:  openai"

  test_openai "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# 🦆 OpenAI via Goose
# ---------------------------------------------------------------
openai-goose)
  BASE="https://api.openai.com/v1"

  update_env "MODEL_PROVIDER"  "openai"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "goose"
  update_env "FALLBACK_CHAIN"  "goose,openai,mock"

  echo "✅ Provider: OpenAI (via Goose)"
  echo "   Endpoint: $BASE"
  echo "   Adapter:  goose"
  ;;

# ---------------------------------------------------------------
# 🔗 Generic HTTP
# ---------------------------------------------------------------
http)
  BASE="http://127.0.0.1:8000/v1"

  update_env "MODEL_PROVIDER"  "http"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "http-agent"
  update_env "FALLBACK_CHAIN"  "http-agent,mock"

  echo "✅ HTTP adapter"
  echo "   Endpoint: $BASE"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

# ---------------------------------------------------------------
# 🧠 Ollama
# ---------------------------------------------------------------
ollama|local)
  BASE="${OLLAMA_ENDPOINT:-http://ollama:11434}"

  update_env "MODEL_PROVIDER"  "local"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "ollama"
  update_env "OLLAMA_MODEL"    "${OLLAMA_MODEL:-tinyllama}"
  update_env "FALLBACK_CHAIN"  "ollama,http-agent,mock"

  echo "✅ Provider:  Ollama (local LLM)"
  echo "   Adapter:   ollama"
  echo "   Endpoint:  $BASE"
  echo "   Model:     ${OLLAMA_MODEL:-tinyllama}"

  test_ollama "$BASE"
  ;;

# ---------------------------------------------------------------
# ☁️ Colab
# ---------------------------------------------------------------
colab)
  if [ -z "${COLAB_URL:-}" ]; then
    echo "❌ COLAB_URL not set — run: ./scripts/start-colab-proxy.sh"
    exit 1
  fi

  BASE="${COLAB_URL}/v1"

  update_env "MODEL_PROVIDER"  "colab"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "http-agent"
  update_env "FALLBACK_CHAIN"  "http-agent,mock"

  echo "✅ Colab GPU"
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

  echo "✅ Mock (offline — no AI calls)"
  ;;

# ---------------------------------------------------------------
# 🧪 Mock-local (mock OpenAI server)
# ---------------------------------------------------------------
mock-local)
  BASE="http://127.0.0.1:8000/v1"

  update_env "MODEL_PROVIDER"  "mock-local"
  update_env "MODEL_ENDPOINT"  "$BASE"
  update_env "AI_ADAPTER"      "http-agent"
  update_env "FALLBACK_CHAIN"  "http-agent,mock"

  echo "✅ Mock OpenAI server"
  echo "   Endpoint: $BASE"
  echo "   Start server first: make mock-server-bg"
  ;;

# ---------------------------------------------------------------
# ❌ Unknown
# ---------------------------------------------------------------
*)
  echo "❌ Unknown provider: $PROVIDER"
  echo "   Options: openai | openai-goose | http | colab | ollama | local | mock | mock-local"
  exit 1
  ;;
esac

echo ""
echo "   Run 'make status' to confirm configuration"
echo ""
