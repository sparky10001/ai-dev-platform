#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (v7 unified)
#
# Features:
# - Unified fallback (shared across ALL adapters)
# - Mock-mode compatible
# - Graceful degradation (no hard crashes)
# - Tool-aware prompting + extraction
###################################################################

set -euo pipefail

ADAPTER_NAME="goose"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"
TOOL_EXECUTOR="${SCRIPT_DIR}/../tool_executor.py"

source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ---- Config ----
GOOSE_BIN="${GOOSE_BIN:-goose}"
MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-2}"
TIMEOUT="${AI_TIMEOUT:-60}"

# ================================================================
# 🧠 MODE DETECTION
# ================================================================

# Mock / disabled mode → skip Goose entirely
if [ "${MODEL_PROVIDER:-}" = "mock" ]; then
    attempt_with_fallback "$INPUT" "mock_mode"
    adapter_exit
fi

# Goose not installed → fallback
if ! command -v "$GOOSE_BIN" >/dev/null 2>&1; then
    attempt_with_fallback "$INPUT" "goose_not_installed"
    adapter_exit
fi

# ================================================================
# 🧠 TOOL RESULT HANDLING
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
    TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

    PROMPT="A tool was used.

Tool: ${TOOL_NAME}
Result:
${TOOL_RESULT}

Decide the next step."

else

    if [ -z "$COMMAND" ]; then
        build_response "error" "Missing command" "invalid_request"
        adapter_exit
    fi

    CONTEXT=""
    [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT]"

    # ---- TOOL DISCOVERY ----
    TOOL_BLOCK=""

    if command -v python3 >/dev/null 2>&1 && [ -f "$TOOL_EXECUTOR" ]; then
        RAW_TOOLS=$(python3 "$TOOL_EXECUTOR" --list-tools 2>/dev/null || echo '{"tools":{}}')

        if echo "$RAW_TOOLS" | jq -e '.tools' >/dev/null 2>&1; then
            TOOL_BLOCK=$(echo "$RAW_TOOLS" | jq -r '
              if (.tools | length) == 0 then ""
              else
                "Available tools:\n" +
                (
                  .tools
                  | to_entries
                  | map("- " + .value.name + ": " + (.value.description // ""))
                  | join("\n")
                )
              end
            ')
        fi
    fi

    SYSTEM_INSTRUCTIONS="You are an AI assistant with access to tools."

    case "$COMMAND" in
      run)      USER_PROMPT="${INPUT}" ;;
      fix)      USER_PROMPT="Fix:\n${INPUT}" ;;
      explain)  USER_PROMPT="Explain:\n${INPUT}" ;;
      refactor) USER_PROMPT="Refactor:\n${INPUT}" ;;
      query)    USER_PROMPT="${INPUT}" ;;
      *)
        build_response "error" "Unknown command: $COMMAND" "invalid_request"
        adapter_exit
        ;;
    esac

    PROMPT="${SYSTEM_INSTRUCTIONS}

${CONTEXT}

${TOOL_BLOCK}

User request:
${USER_PROMPT}"
fi

# ================================================================
# 🚀 EXECUTION LOOP
# ================================================================

ATTEMPT=1
RESPONSE=""

while [ "$ATTEMPT" -le "$RETRIES" ]; do

    RESPONSE=$(echo "$PROMPT" | timeout "$TIMEOUT" "$GOOSE_BIN" run \
        --no-session \
        --provider openai \
        --model "$MODEL" \
        --text - 2>/dev/null || true)

    # ---- Valid output ----
    if [ -n "$RESPONSE" ] && echo "$RESPONSE" | grep -q '[^[:space:]]'; then
        break
    fi

    sleep $ATTEMPT
    ATTEMPT=$((ATTEMPT + 1))
done

# ================================================================
# ❌ FAILURE → FALLBACK
# ================================================================

if [ -z "$RESPONSE" ] || ! echo "$RESPONSE" | grep -q '[^[:space:]]'; then
    attempt_with_fallback "$PROMPT" "goose_failure"
    adapter_exit
fi

# ================================================================
# 🔥 TOOL CALL DETECTION
# ================================================================

TOOL_CALL_JSON=$(extract_tool_call "$RESPONSE" || true)

if [ -n "$TOOL_CALL_JSON" ]; then
    TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name')
    TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')

    build_tool_call "$TOOL_NAME" "$TOOL_INPUT"
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