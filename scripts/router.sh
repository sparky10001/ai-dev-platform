#!/bin/bash
###################################################################
# router.sh — Unified AI Adapter Router (v1 production)
#
# Responsibilities:
# - Route commands to selected adapter
# - Enforce adapter contract boundary
# - Optional multi-provider fallback chain
#
# DOES NOT:
# - Re-implement adapter logic
# - Parse model responses deeply
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

COMMAND="${1:-}"
INPUT="${2:-}"

# ================================================================
# 🔧 CONFIG
# ================================================================

PRIMARY_ADAPTER="${MODEL_PROVIDER:-http}"

# Optional fallback chain (ordered)
# Example:
# export ROUTER_FALLBACK_CHAIN="mock goose http"
FALLBACK_CHAIN="${ROUTER_FALLBACK_CHAIN:-}"

# Adapter map
get_adapter_path() {
  case "$1" in
    http)    echo "${SCRIPT_DIR}/adapters/http-agent.sh" ;;
    openai)  echo "${SCRIPT_DIR}/adapters/openai.sh" ;;
    goose)   echo "${SCRIPT_DIR}/adapters/goose.sh" ;;
    mock)    echo "${SCRIPT_DIR}/adapters/mock.sh" ;;
    *)
      echo ""
      ;;
  esac
}

# ================================================================
# 🧠 EXECUTION WRAPPER
# ================================================================

run_adapter() {
  local adapter="$1"

  local path
  path=$(get_adapter_path "$adapter")

  if [ -z "$path" ] || [ ! -f "$path" ]; then
    return 1
  fi

  RESPONSE=$("$path" "$COMMAND" "$INPUT" 2>/dev/null || true)

  if [ -z "$RESPONSE" ]; then
    return 1
  fi

  echo "$RESPONSE"
  return 0
}

# ================================================================
# 🔍 RESPONSE CHECK
# ================================================================

is_success() {
  echo "$1" | jq -e '.status == "done" or .status == "tool_call"' >/dev/null 2>&1
}

# ================================================================
# 🚀 PRIMARY EXECUTION
# ================================================================

RESPONSE="$(run_adapter "$PRIMARY_ADAPTER" || true)"

if is_success "$RESPONSE"; then
  echo "$RESPONSE"
  exit 0
fi

# ================================================================
# 🔁 ROUTER-LEVEL FALLBACK CHAIN (OPTIONAL)
# ================================================================

if [ -n "$FALLBACK_CHAIN" ]; then

  for adapter in $FALLBACK_CHAIN; do

    # Skip primary (already attempted)
    if [ "$adapter" = "$PRIMARY_ADAPTER" ]; then
      continue
    fi

    RESPONSE="$(run_adapter "$adapter" || true)"

    if is_success "$RESPONSE"; then
      echo "$RESPONSE"
      exit 0
    fi
  done
fi

# ================================================================
# ❌ FINAL FAILURE
# ================================================================

jq -n \
  --arg provider "$PRIMARY_ADAPTER" \
  --arg msg "All adapters failed" \
  '{
    status: "error",
    output: $msg,
    next_input: null,
    tool_call: null,
    meta: {
      adapter: "router",
      provider: $provider,
      error_type: "router_failure"
    }
  }'