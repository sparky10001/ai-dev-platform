#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (v5 production)
#
# Features:
# - Full _base.sh integration (single contract authority)
# - Tool-aware prompting (via tool_executor.py)
# - Tool result handling (runtime-compatible)
# - Hardened retry loop (no empty/garbage responses)
# - Timeout protection (prevents hanging CLI)
# - Zero non-zero exits (CI-safe)
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
TIMEOUT="${AI_TIMEOUT:-60}"

# ================================================================
# 🧠 VALIDATION
# ================================================================

if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
fi

if ! command -v "$GOOSE_BIN" >/dev/null 2>&1; then
    build_response "error" "Goose not installed" "system_failure"
    adapter_exit
fi

if [ "${MODEL_PROVIDER:-openai}" != "openai" ]; then
    build_response "error" \
      "Goose requires MODEL_PROVIDER=openai" \
      "invalid_request"
    adapter_exit
fi

# ================================================================
# 🧠 TOOL RESULT HANDLING (CRITICAL)
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
    TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

    PROMPT="Tool '${TOOL_NAME}' returned:\n${TOOL_RESULT}\n\nContinue solving the task using this result."

else

    # ---- Context ----
    CONTEXT=""
    [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

    # ================================================================
    # 🔌 TOOL-AWARE PROMPTING (FIXED + STANDARDIZED)
    # ================================================================
    TOOL_CONTEXT=""

    if command -v python3 >/dev/null 2>&1 && [ -f "${SCRIPT_DIR}/../tool_executor.py" ]; then
        TOOL_METADATA=$(python3 "${SCRIPT_DIR}/../tool_executor.py" --list-tools 2>/dev/null || echo "{}")

        TOOL_CONTEXT="\n\nAvailable tools (JSON):\n${TOOL_METADATA}\n\nUse tools when appropriate."
    fi

    # ---- Prompt builder ----
    case "$COMMAND" in
      run)      PROMPT="${CONTEXT}${INPUT}${TOOL_CONTEXT}" ;;
      fix)      PROMPT="${CONTEXT}Fix this:\n${INPUT}${TOOL_CONTEXT}" ;;
      explain)  PROMPT="${CONTEXT}Explain clearly:\n${INPUT}${TOOL_CONTEXT}" ;;
      refactor) PROMPT="${CONTEXT}Refactor this:\n${INPUT}${TOOL_CONTEXT}" ;;
      query)    PROMPT="${CONTEXT}${INPUT}${TOOL_CONTEXT}" ;;
      *)
        build_response "error" "Unknown command: $COMMAND" "invalid_request"
        adapter_exit
        ;;
    esac
fi

# ================================================================
# 🚀 EXECUTION LOOP (HARDENED)
# ================================================================

ATTEMPT=1
RESPONSE=""

while [ "$ATTEMPT" -le "$RETRIES" ]; do

    RESPONSE=$(echo "$PROMPT" | timeout "$TIMEOUT" "$GOOSE_BIN" run \
        --no-session \
        --provider openai \
        --model "$MODEL" \
        --text - 2>/dev/null || true)

    # ---- Empty / garbage guard ----
    if [ -n "$RESPONSE" ] && echo "$RESPONSE" | grep -q '[^[:space:]]'; then
        break
    fi

    sleep $ATTEMPT
    ATTEMPT=$((ATTEMPT + 1))
done

# ================================================================
# ❌ FAILURE
# ================================================================

if [ -z "$RESPONSE" ] || ! echo "$RESPONSE" | grep -q '[^[:space:]]'; then
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
  "$(jq -n \
    --arg model "$MODEL" \
    --arg provider "goose" \
    '{model: $model, mode: "cli", provider: $provider}')"

adapter_exit