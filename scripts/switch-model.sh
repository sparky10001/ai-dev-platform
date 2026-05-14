#!/bin/bash
###################################################################
# switch-model.sh — v7.1 (Phase 3E runtime-adapter aligned)
#
# Provider switching changes MODEL_PROVIDER / MODEL_ENDPOINT.
# Runtime adapter remains agent.
###################################################################

set -euo pipefail

PROVIDER="${1:-}"
shift || true

ENV_FILE="$(dirname "$0")/../.env"

# ---------------------------------------------------------------
# Flags
# ---------------------------------------------------------------
MANUAL=0
DRY_RUN=0
CUSTOM_ENDPOINT=""
CUSTOM_MODEL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manual) MANUAL=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --endpoint) CUSTOM_ENDPOINT="$2"; shift ;;
    --model) CUSTOM_MODEL="$2"; shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------
# Validate input
# ---------------------------------------------------------------
if [ -z "$PROVIDER" ]; then
  echo "Usage: switch-model.sh [provider] [--manual] [--endpoint URL] [--model NAME] [--dry-run]"
  exit 1
fi

touch "$ENV_FILE"

set -a
source "$ENV_FILE"
set +a

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
update_env() {
  local key="$1"
  local val="$2"

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[DRY RUN] $key=$val"
    return
  fi

  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

strip_v1() {
  echo "$1" | sed 's|/v1$||'
}

test_openai_compatible() {
  if [ "$MANUAL" -eq 1 ]; then
    echo "⚠️  Manual mode: skipping endpoint test"
    return 0
  fi

  local base="$1"

  echo ""
  echo "🔍 Testing endpoint..."

  RESP="$(curl -sS \
    --connect-timeout 3 \
    --max-time 5 \
    "${base}/models" || true)"

  if echo "$RESP" | jq -e '.data' >/dev/null 2>&1; then
    echo "✅ Endpoint OK"
    return 0
  fi

  if echo "$RESP" | jq -e '.error' >/dev/null 2>&1; then
    echo "⚠️  Auth required (acceptable)"
    return 0
  fi

  echo "❌ Endpoint failed"

  if [ "$MANUAL" -eq 0 ]; then
    exit 1
  fi
}

# ---------------------------------------------------------------
# Start
# ---------------------------------------------------------------
echo ""
echo "🔄 Switching provider → $PROVIDER"

[ "$MANUAL" -eq 1 ] && echo "⚙️  Manual mode enabled"
[ "$DRY_RUN" -eq 1 ] && echo "🧪 Dry-run mode enabled"

# ---------------------------------------------------------------
# Provider Switch
# ---------------------------------------------------------------
case "$PROVIDER" in

litellm)
  BASE="${CUSTOM_ENDPOINT:-${LITELLM_BASE_URL:-http://litellm:4000/v1}}"
  MODEL="${CUSTOM_MODEL:-${LITELLM_MODEL:-fast}}"
  KEY="${LITELLM_MASTER_KEY:-ai-dev-platform}"

  update_env "MODEL_PROVIDER" "litellm"
  update_env "MODEL_ENDPOINT" "$BASE"
  update_env "AI_ADAPTER" "agent"
  update_env "LITELLM_MODEL" "$MODEL"
  update_env "LITELLM_MASTER_KEY" "$KEY"
  update_env "FALLBACK_CHAIN" "litellm,mock"

  echo "✅ LiteLLM"
  echo "   Endpoint: $BASE"
  echo "   Model:    $MODEL"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

goose)
  BASE="${CUSTOM_ENDPOINT:-${LITELLM_BASE_URL:-http://litellm:4000/v1}}"
  MODEL="${CUSTOM_MODEL:-${GOOSE_MODEL:-fast}}"

  update_env "MODEL_PROVIDER" "goose"
  update_env "MODEL_ENDPOINT" "$BASE"
  update_env "AI_ADAPTER" "agent"
  update_env "GOOSE_PROVIDER" "litellm"
  update_env "GOOSE_MODEL" "$MODEL"
  update_env "FALLBACK_CHAIN" "litellm,mock"

  echo "🦆 Goose mode"
  echo "   Endpoint: $BASE"
  echo "   Model:    $MODEL"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

colab)
  BASE="${CUSTOM_ENDPOINT:-${COLAB_URL:-}}"

  if [ -z "$BASE" ]; then
    echo "❌ COLAB_URL not set"
    exit 1
  fi

  BASE="${BASE}/v1"

  update_env "MODEL_PROVIDER" "colab"
  update_env "MODEL_ENDPOINT" "$BASE"
  update_env "AI_ADAPTER" "agent"
  update_env "FALLBACK_CHAIN" "litellm,mock"

  echo "☁️ Colab"
  echo "   Endpoint: $BASE"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

mock)
  update_env "MODEL_PROVIDER" "mock"
  update_env "MODEL_ENDPOINT" "none"
  update_env "AI_ADAPTER" "agent"
  update_env "FALLBACK_CHAIN" "mock"

  echo "🧪 Mock (offline)"
  ;;

mock-local)
  BASE="${CUSTOM_ENDPOINT:-http://127.0.0.1:8000/v1}"

  update_env "MODEL_PROVIDER" "mock-local"
  update_env "MODEL_ENDPOINT" "$BASE"
  update_env "AI_ADAPTER" "agent"
  update_env "FALLBACK_CHAIN" "litellm,mock"

  echo "🧪 Mock-local"
  echo "   Endpoint: $BASE"

  test_openai_compatible "$(strip_v1 "$BASE")"
  ;;

*)
  echo "❌ Unknown provider: $PROVIDER"
  exit 1
  ;;
esac

echo ""
echo "✅ Done"
echo "   Run: make status"
echo ""