#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (v8.0 PRODUCTION)
#
# Architecture:
# - Goose = runtime adapter (NOT provider)
# - LiteLLM handles model routing
# - MCP-style tool calling supported
# - Fully fallback-safe
#
# Improvements:
# - Hardened retries + timeout
# - Proper fallback integration
# - Tool-safe JSON extraction
# - Empty/invalid response handling
###################################################################

set -euo pipefail

ADAPTER_NAME="goose"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"
TOOL_EXECUTOR="${SCRIPT_DIR}/../tool_executor.py"

source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

# ================================================================
# 🔧 Load Environment
# ================================================================
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ================================================================
# ⚙️ Config
# ================================================================
GOOSE_BIN="${GOOSE_BIN:-goose}"
MODEL="${ACTIVE_MODEL:-fast}"
RETRIES="${AI_RETRIES:-2}"
TIMEOUT="${AI_TIMEOUT:-60}"

# Detect fallback mode
IS_FALLBACK="${FALLBACK_ACTIVE:-false}"

# ================================================================
# 🚫 Fast Exit Conditions
# ================================================================

# If explicitly in mock provider → skip Goose
if [ "${MODEL_PROVIDER:-}" = "mock" ]; then
    attempt_with_fallback "$INPUT" "mock_mode"
    adapter_exit
fi

# Goose CLI not installed
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

    PROMPT="A tool was executed.

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

    # ------------------------------------------------------------
    # 🔧 Tool Discovery (MCP-style)
    # ------------------------------------------------------------
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

    SYSTEM_INSTRUCTIONS="You are an AI agent with access to tools.
Follow tool usage rules strictly.
Respond clearly and deterministically."

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
        --text - 2>/dev/null || true)

    # Valid non-empty response
    if [ -n "$RESPONSE" ] && echo "$RESPONSE" | grep -q '[^[:space:]]'; then
        break
    fi

    sleep "$ATTEMPT"
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
TOOL_CALL_JSON="$(extract_tool_call "$RESPONSE" || true)"

if [ -n "$TOOL_CALL_JSON" ] && echo "$TOOL_CALL_JSON" | jq -e . >/dev/null 2>&1; then
    TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name // empty')
    TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')

    if [ -n "$TOOL_NAME" ]; then
        build_tool_call "$TOOL_NAME" "$TOOL_INPUT"
        adapter_exit
    fi
fi

# ================================================================
# ✅ SUCCESS
# ================================================================
build_response "done" "$RESPONSE" "" \
  "$(jq -n \
    --arg model "$MODEL" \
    --arg provider "goose" \
    --arg mode "cli" \
    '{model: $model, provider: $provider, mode: $mode}')"

adapter_exit