#!/bin/bash
###################################################################
# openai.sh — Contract-Based OpenAI Adapter (v7.1)
#
# No changes from sanity check — already correctly:
# - Uses attempt_with_fallback on failure
# - Does NOT fallback on auth errors
# - No symlinks
###################################################################

set -euo pipefail

ADAPTER_NAME="openai"

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
MODEL="${MODEL_NAME:-gpt-4o-mini}"
ENDPOINT="${MODEL_ENDPOINT:-https://api.openai.com/v1}"
API_KEY="${OPENAI_API_KEY:-}"
TEMPERATURE="${MODEL_TEMPERATURE:-0.7}"
MAX_TOKENS="${MODEL_MAX_TOKENS:-512}"
RETRIES="${AI_RETRIES:-3}"
TIMEOUT="${AI_TIMEOUT:-30}"

# ================================================================
# 🧠 MODE DETECTION
# ================================================================

if [ -z "$ENDPOINT" ] || [ "$ENDPOINT" = "none" ] || [ "$ENDPOINT" = "null" ]; then
  attempt_with_fallback "$INPUT" "no_endpoint_or_mock"
  adapter_exit
fi

# Hard fail — missing API key for OpenAI (no fallback — config error)
if [ -z "$API_KEY" ] && [[ "$ENDPOINT" == *"openai.com"* ]]; then
  build_response "error" "Missing OPENAI_API_KEY" "invalid_api_key"
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
# 📦 REQUEST
# ================================================================
build_payload() {
  jq -n \
    --arg model "$MODEL" \
    --arg prompt "$PROMPT" \
    --argjson temp "$TEMPERATURE" \
    --argjson max_tokens "$MAX_TOKENS" \
    '{
      model: $model,
      messages: [
        { role: "system", content: "You are a helpful AI assistant." },
        { role: "user", content: $prompt }
      ],
      temperature: $temp,
      max_tokens: $max_tokens
    }'
}

request_once() {
  curl -sS \
    --max-time "$TIMEOUT" \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(build_payload)" 2>/dev/null || true
}

# ================================================================
# 🔁 RETRY LOOP
# ================================================================
attempt=1
RESPONSE=""

while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once)"

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

      build_tool_call "$TOOL_NAME" "$TOOL_INPUT"
      adapter_exit
    fi

    build_response "done" "$OUTPUT" "" \
      "$(jq -n --arg model "$MODEL" --arg endpoint "$ENDPOINT" \
        '{model:$model, endpoint:$endpoint, mode:"openai"}')"

    adapter_exit
  fi

  # ❌ API ERROR
  if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then

    ERR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')
    ERR_TYPE_RAW=$(echo "$RESPONSE" | jq -r '.error.type // "api_error"')
    ERR_TYPE=$(classify_error "$ERR_TYPE_RAW" "$ERR_MSG")

    case "$ERR_TYPE" in
      invalid_api_key|invalid_request)
        # Non-retryable — no fallback for config errors
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
# 🔥 FALLBACK
# ================================================================
attempt_with_fallback "$PROMPT" "openai_failure"
