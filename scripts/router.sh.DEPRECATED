#!/usr/bin/env bash
###################################################################
# router.sh — Minimal Router (LiteLLM primary, Mock fallback)
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---------------------------------------------------------------
# Load env
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ---------------------------------------------------------------
# Loop protection
# ---------------------------------------------------------------
if [ "${ROUTER_ACTIVE:-false}" = "true" ]; then
  echo "❌ Router recursion detected"
  exit 1
fi

export ROUTER_ACTIVE=true

LITELLM="${SCRIPT_DIR}/adapters/litellm.sh"
MOCK="${SCRIPT_DIR}/adapters/mock.sh"

# ---------------------------------------------------------------
# Validate adapters exist
# ---------------------------------------------------------------
if [ ! -f "$LITELLM" ]; then
  echo "❌ litellm.sh not found"
  exit 1
fi

if [ ! -f "$MOCK" ]; then
  echo "❌ mock.sh not found"
  exit 1
fi

# ---------------------------------------------------------------
# Run LiteLLM (primary)
# ---------------------------------------------------------------
if RESPONSE="$("$LITELLM" "$COMMAND" "$INPUT" 2>/dev/null)" \
   && [ -n "$RESPONSE" ] \
   && echo "$RESPONSE" | jq -e . >/dev/null 2>&1; then

  echo "$RESPONSE"
  exit 0
fi

# ---------------------------------------------------------------
# Fallback to mock
# ---------------------------------------------------------------
echo "⚠️ LiteLLM failed — falling back to mock" >&2

export FALLBACK_ACTIVE=true

RESPONSE="$("$MOCK" "$COMMAND" "$INPUT" 2>/dev/null || true)"

if [ -n "$RESPONSE" ]; then
  echo "$RESPONSE"
  exit 0
fi

# ---------------------------------------------------------------
# Final failure (should never happen)
# ---------------------------------------------------------------
jq -n '{
  status: "error",
  output: "Both LiteLLM and mock failed",
  tool_call: null,
  meta: {router: "minimal"}
}'