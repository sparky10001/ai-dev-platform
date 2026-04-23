#!/bin/bash
###################################################################
# http-agent.sh — Contract-based HTTP adapter (v6.1)
#
# No changes needed from sanity check —
# already correctly uses attempt_with_fallback on failure
# No symlinks
###################################################################

set -euo pipefail

ADAPTER_NAME="http-agent"

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
ENDPOINT="${MODEL_ENDPOINT:-}"
MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-3}"
TIMEOUT="${AI_TIMEOUT:-30}"
TEMPERATURE="${MODEL_TEMPERATURE:-0.7}"

# ================================================================
# 🧠 HARD MODE DETECTION
# ================================================================

# Normalize endpoint
if [ -z "$ENDPOINT" ] || [ "$ENDPOINT" = "none" ] || [ "$ENDPOINT" = "null" ]; then
  ENDPOINT=""
fi

# No endpoint → fallback immediately
if [ -z "$ENDPOINT" ]; then
  attempt_with_fallback "$INPUT" "no_endpoint_or_mock"
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

Decide the next step:
- If the task is complete, provide the final answer
- If more data is needed, call another tool"

else

  if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
  fi

  CONTEXT=""
  [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT]"

  # ---- Tool discovery ----
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
    fix)      USER_PROMPT="Fix this:\n${INPUT}" ;;
    explain)  USER_PROMPT="Explain clearly:\n${INPUT}" ;;
    refactor) USER_PROMPT="Refactor this:\n${INPUT}" ;;
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
# 📦 REQUEST
# ================================================================
build_payload() {
  jq -n \
    --arg model "$MODEL" \
    --arg prompt "$PROMPT" \
    --argjson temp "$TEMPERATURE" \
    '{
      model: $model,
      messages: [{ role: "user", content: $prompt }],
      temperature: $temp
    }'
}

request_once() {
  curl -sS --fail-with-body \
    --max-time "$TIMEOUT" \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
    -d "$(build_payload)" 2>/dev/null || true
}

# ================================================================
# 🔁 RETRY LOOP
# ================================================================
attempt=1
RESPONSE=""

while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once)"

  # Empty or invalid JSON → retry
  if [ -z "$RESPONSE" ] || ! json_valid "$RESPONSE"; then
    sleep $((attempt * 2))
    attempt=$((attempt + 1))
    continue
  fi

  # ✅ SUCCESS
  if echo "$RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then

    OUTPUT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')

    TOOL_CALL_JSON=$(extract_tool_call "$OUTPUT" || true)

    if [ -n "$TOOL_CALL_JSON" ]; then
      TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name')
      TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')

      build_tool_call "$TOOL_NAME" "$TOOL_INPUT" "Model requested tool"
      adapter_exit
    fi

    build_response "done" "$OUTPUT" "" \
      "$(jq -n --arg endpoint "$ENDPOINT" --arg model "$MODEL" \
        '{endpoint: $endpoint, model: $model, mode: "http"}')"

    adapter_exit
  fi

  # ❌ API ERROR
  if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then

    ERR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')
    ERR_TYPE_RAW=$(echo "$RESPONSE" | jq -r '.error.type // "api_error"')
    ERR_TYPE=$(classify_error "$ERR_TYPE_RAW" "$ERR_MSG")

    case "$ERR_TYPE" in
      invalid_api_key|invalid_request)
        # Non-retryable — return error directly, no fallback
        build_response "error" "$ERR_MSG" "$ERR_TYPE"
        adapter_exit
        ;;
      insufficient_quota|rate_limit_exceeded)
        sleep $((attempt * 2))
        ;;
    esac
  fi

  attempt=$((attempt + 1))
done

# ================================================================
# 🔥 TRUE FAILURE → FALLBACK
# ================================================================
attempt_with_fallback "$PROMPT" "http_agent_failure"
