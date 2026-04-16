#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (v5.2 production)
#
# Fully aligned with http-agent + openai adapters
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
# 🧠 TOOL RESULT HANDLING (FIRST)
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
    TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

    PROMPT="Tool '${TOOL_NAME}' returned:
${TOOL_RESULT}

Continue solving the task using this result."

else

    # ---- Validate ----
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

    # ---- Context ----
    CONTEXT=""
    [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

    # ================================================================
    # 🔌 TOOL DISCOVERY (ALIGNED)
    # ================================================================
    TOOL_BLOCK=""

    if command -v python3 >/dev/null 2>&1 && [ -f "${SCRIPT_DIR}/../tool_executor.py" ]; then

        RAW_TOOLS=$(python3 "${SCRIPT_DIR}/../tool_executor.py" --list-tools 2>/dev/null || echo '{"tools":{}}')

        if echo "$RAW_TOOLS" | jq -e '.tools' >/dev/null 2>&1; then
            TOOL_BLOCK=$(echo "$RAW_TOOLS" | jq -r '
              if (.tools | length) == 0 then
                ""
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

    # ---- Prompt builder ----
    case "$COMMAND" in
      run)      USER_PROMPT="${INPUT}" ;;
      fix)      USER_PROMPT="Fix this:\n${INPUT}" ;;
      explain)  USER_PROMPT="Explain clearly:\n${INPUT}" ;;
      refactor) USER_PROMPT="Refactor this:\n${INPUT}" ;;
      query)    USER_PROMPT="${INPUT}" ;;
      *)
        build_response "error" "Unknown command: $COMMAND" "invalid_request"
        adapter_exit
        ;;
    esac

    PROMPT="${CONTEXT}${TOOL_BLOCK}

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
# 🔥 TOOL CALL DETECTION (CRITICAL PARITY)
# ================================================================

TOOL_CALL_JSON=$(extract_tool_call "$RESPONSE" || true)

if [ -n "$TOOL_CALL_JSON" ]; then
  TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name')
  TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')

  build_tool_call "$TOOL_NAME" "$TOOL_INPUT" "Model requested tool"
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