#!/bin/bash
###################################################################
# openai.sh — Contract-Based OpenAI Adapter (Production v4)
#
# Built on _base.sh (single contract authority)
###################################################################

set -euo pipefail

# ---- Adapter identity ----
ADAPTER_NAME="openai"

# ---- Load base ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Load env ----
ENV_FILE="${SCRIPT_DIR}/../../.env"
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

# ---- Validate inputs ----
if [ -z "$COMMAND" ]; then
  build_response "error" "No command provided" "invalid_request"
  adapter_exit
fi

if [ -z "$API_KEY" ] && [[ "$ENDPOINT" == *"openai.com"* ]]; then
  build_response "error" "Missing OPENAI_API_KEY" "invalid_api_key"
  adapter_exit
fi

# ---- Context ----
CONTEXT=""
[ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

# ---- Prompt builder ----
case "$COMMAND" in
  run)      PROMPT="${CONTEXT}${INPUT}" ;;
  explain)  PROMPT="${CONTEXT}Explain clearly:\n${INPUT}" ;;
  fix)      PROMPT="${CONTEXT}Fix this:\n${INPUT}" ;;
  refactor) PROMPT="${CONTEXT}Refactor this:\n${INPUT}" ;;
  query)    PROMPT="${CONTEXT}${INPUT}" ;;
  *)
    build_response "error" "Unknown command" "invalid_request"
    adapter_exit
    ;;
esac

# ---- Payload builder (SAFE via jq) ----
build_payload() {
  if [ "$JSON_MODE" = "true" ]; then
    jq -n \
      --arg model "$MODEL" \
      --arg prompt "$PROMPT" \
      --argjson temp "$TEMPERATURE" \
      --argjson max_tokens "$MAX_TOKENS" \
      '{
        model: $model,
        temperature: $temp,
        max_tokens: $max_tokens,
        response_format: {type: "json_object"},
        messages: [
          {role: "system", content: "You are a helpful AI assistant."},
          {role: "user", content: $prompt}
        ]
      }'
  else
    jq -n \
      --arg model "$MODEL" \
      --arg prompt "$PROMPT" \
      --argjson temp "$TEMPERATURE" \
      --argjson max_tokens "$MAX_TOKENS" \
      '{
        model: $model,
        temperature: $temp,
        max_tokens: $max_tokens,
        messages: [
          {role: "system", content: "You are a helpful AI assistant."},
          {role: "user", content: $prompt}
        ]
      }'
  fi
}

# ---- Single request ----
request_once() {
  curl -sS "$ENDPOINT/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(build_payload)" || true
}

# ---- Retry loop ----
attempt=1
while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once)"

  # ---- Validate JSON ----
  if ! json_valid "$RESPONSE"; then
    sleep $((attempt * 2))
    attempt=$((attempt + 1))
    continue
  fi

  # ---- SUCCESS ----
  if echo "$RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
    OUTPUT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')
    build_response "done" "$OUTPUT"
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

# ---- Final failure ----
build_response "error" "OpenAI request failed after $RETRIES attempts" "api_error"
adapter_exit