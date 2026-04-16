#!/bin/bash
###################################################################
# openai.sh — Contract-Based OpenAI Adapter (v6 production)
#
# FULLY ALIGNED with http-agent v5:
# - Tool-aware prompting (clean + structured)
# - Tool result handling (first-class)
# - Tool call extraction (CRITICAL)
# - Safe retry + JSON validation
# - Contract-safe outputs
###################################################################

set -euo pipefail

# ---- Adapter identity ----
ADAPTER_NAME="openai"

# ---- Paths ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"
TOOL_EXECUTOR="${SCRIPT_DIR}/../tool_executor.py"

# ---- Load base ----
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
JSON_MODE="${AI_JSON_MODE:-false}"
RETRIES="${AI_RETRIES:-3}"
TIMEOUT="${AI_TIMEOUT:-30}"

# ================================================================
# 🧠 TOOL RESULT HANDLING (CRITICAL)
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
  TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

  PROMPT="A tool was used.

Tool: ${TOOL_NAME}
Result:
${TOOL_RESULT}

Decide the next step:
- If the task is complete, provide the final answer.
- If more data is needed, call another tool."

else

  # ---- Validate ----
  if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
  fi

  if [ -z "$API_KEY" ] && [[ "$ENDPOINT" == *"openai.com"* ]]; then
    build_response "error" "Missing OPENAI_API_KEY" "invalid_api_key"
    adapter_exit
  fi

  # ---- Context ----
  CONTEXT=""
  [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

  # ================================================================
  # 🔌 TOOL DISCOVERY (CLEAN + SAFE)
  # ================================================================
  TOOL_BLOCK=""

  if command -v python3 >/dev/null 2>&1 && [ -f "$TOOL_EXECUTOR" ]; then

      RAW_TOOLS=$(python3 "$TOOL_EXECUTOR" --list-tools 2>/dev/null || echo '{"tools":{}}')

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

  # ================================================================
  # 🧠 TOOL USAGE INSTRUCTIONS (CRITICAL)
  # ================================================================
  SYSTEM_INSTRUCTIONS="You are an AI assistant with access to tools.

When you need external data, you MUST call a tool.

To call a tool, respond ONLY with valid JSON:
{
  \"status\": \"tool_call\",
  \"tool_call\": {
    \"name\": \"tool_name\",
    \"input\": { ... }
  }
}

Rules:
- Do NOT include explanations when calling tools
- ONLY output JSON for tool calls
- If no tool is needed, respond normally"

  # ---- Prompt ----
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

${CONTEXT}${TOOL_BLOCK}

User request:
${USER_PROMPT}"
fi

# ================================================================
# 📦 BUILD REQUEST
# ================================================================
build_payload() {
  if [ "$JSON_MODE" = "true" ]; then
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
        max_tokens: $max_tokens,
        response_format: { type: "json_object" }
      }'
  else
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
  fi
}

# ---- Single request ----
request_once() {
  curl -sS \
    --max-time "$TIMEOUT" \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(build_payload)" || true
}

# ================================================================
# 🔁 RETRY LOOP
# ================================================================
attempt=1
while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once)"

  if [ -z "$RESPONSE" ]; then
    sleep $((attempt * 2))
    attempt=$((attempt + 1))
    continue
  fi

  if ! json_valid "$RESPONSE"; then
    sleep $((attempt * 2))
    attempt=$((attempt + 1))
    continue
  fi

  # ---- SUCCESS ----
  if echo "$RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    OUTPUT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')

    # Empty guard
    if [ -z "$OUTPUT" ]; then
      sleep $((attempt * 2))
      attempt=$((attempt + 1))
      continue
    fi

    # 🔥 Tool call detection (CRITICAL)
    TOOL_CALL_JSON=$(extract_tool_call "$OUTPUT" || true)

    if [ -n "$TOOL_CALL_JSON" ]; then
      TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name')
      TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')

      build_tool_call "$TOOL_NAME" "$TOOL_INPUT" "Model requested tool"
      adapter_exit
    fi

    build_response "done" "$OUTPUT" "" \
      "$(jq -n --arg model "$MODEL" --arg endpoint "$ENDPOINT" '{model: $model, endpoint: $endpoint, mode: "openai"}')"

    adapter_exit
  fi

  # ---- ERROR ----
  if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    ERR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')
    ERR_TYPE_RAW=$(echo "$RESPONSE" | jq -r '.error.type // "api_error"')
    ERR_TYPE=$(classify_error "$ERR_TYPE_RAW" "$ERR_MSG")

    case "$ERR_TYPE" in
      invalid_api_key|insufficient_quota|invalid_request)
        build_response "error" "$ERR_MSG" "$ERR_TYPE"
        adapter_exit
        ;;
    esac
  fi

  sleep $((attempt * 2))
  attempt=$((attempt + 1))
done

# ================================================================
# ❌ FINAL FAILURE
# ================================================================
build_response "error" "OpenAI request failed after $RETRIES attempts" "api_error" \
  "$(jq -n --arg endpoint "$ENDPOINT" '{endpoint: $endpoint}')"

adapter_exit