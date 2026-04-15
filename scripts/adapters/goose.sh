#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (v4 unified)
#
# Features:
# - Uses shared _base.sh contract
# - Safe retry handling
# - No non-zero exits
# - Context-aware prompting
# - Fully aligned with runtime + other adapters
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Adapter identity ----
ADAPTER_NAME="goose"

# ---- Load shared base ----
source "${SCRIPT_DIR}/_base.sh"

# ---- Config ----
GOOSE_BIN="${GOOSE_BIN:-goose}"
ENV_FILE="${SCRIPT_DIR}/../../.env"

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-2}"

# ================================================================
# 🧠 VALIDATION
# ================================================================

# Missing command
if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
fi

# Goose binary check
if ! command -v "$GOOSE_BIN" >/dev/null 2>&1; then
    build_response "error" "Goose not installed" "system_failure"
    adapter_exit
fi

# Provider check
if [ "${MODEL_PROVIDER:-openai}" != "openai" ]; then
    build_response "error" \
      "Goose requires MODEL_PROVIDER=openai" \
      "invalid_request"
    adapter_exit
fi

# ================================================================
# 🧠 TOOL RESULT HANDLING (future-proofing)
# ================================================================
# Goose doesn't support tools natively (yet),
# but we gracefully handle injected tool results

if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool')
    TOOL_RESULT=$(echo "$INPUT" | jq -r '.result')

    PROMPT="Tool '$TOOL_NAME' returned:\n$TOOL_RESULT\n\nContinue the task."
else
    # ---- Context ----
    CONTEXT=""
    [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

    # ---- Prompt builder ----
    case "$COMMAND" in
      run)      PROMPT="${CONTEXT}${INPUT}" ;;
      fix)      PROMPT="${CONTEXT}Fix this:\n${INPUT}" ;;
      explain)  PROMPT="${CONTEXT}Explain clearly:\n${INPUT}" ;;
      refactor) PROMPT="${CONTEXT}Refactor this:\n${INPUT}" ;;
      query)    PROMPT="${CONTEXT}${INPUT}" ;;
      *)
        build_response "error" "Unknown command: $COMMAND" "invalid_request"
        adapter_exit
        ;;
    esac
fi

# ================================================================
# 🚀 EXECUTION LOOP
# ================================================================

ATTEMPT=1
RESPONSE=""

while [ "$ATTEMPT" -le "$RETRIES" ]; do

    RESPONSE=$(echo "$PROMPT" | "$GOOSE_BIN" run \
        --no-session \
        --provider openai \
        --model "$MODEL" \
        --text - 2>/dev/null || true)

    if [ -n "$RESPONSE" ]; then
        break
    fi

    sleep $ATTEMPT
    ATTEMPT=$((ATTEMPT + 1))
done

# ================================================================
# ❌ FAILURE
# ================================================================

if [ -z "$RESPONSE" ]; then
    build_response \
      "error" \
      "Goose failed after $RETRIES attempts" \
      "api_error" \
      "{\"retries\":$RETRIES}"
    adapter_exit
fi

# ================================================================
# ✅ SUCCESS
# ================================================================

build_response "done" "$RESPONSE" "" \
  "{\"model\":\"$MODEL\",\"mode\":\"cli\"}"

adapter_exit