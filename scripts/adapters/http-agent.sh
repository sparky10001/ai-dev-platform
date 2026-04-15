#!/bin/bash
###################################################################
# http-agent.sh — Contract-based HTTP adapter (v4 production)
#
# Fully aligned with _base.sh + runtime contract
###################################################################

set -euo pipefail

# ---- Adapter identity ----
ADAPTER_NAME="http-agent"

# ---- Paths ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"

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
ENDPOINT="${MODEL_ENDPOINT:-http://localhost:8000/v1}"
MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-3}"
TIMEOUT="${AI_TIMEOUT:-30}"
TEMPERATURE="${MODEL_TEMPERATURE:-0.7}"
JSON_MODE="${AI_JSON_MODE:-false}"

# ---- Validate ----
if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
fi

# ---- Context ----
CONTEXT=""
[ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

# ---- Prompt ----
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

# ---- Build request (safe jq) ----
build_payload() {
  if [ "$JSON_MODE" = "true" ]; then
    jq -n \
      --arg model "$MODEL" \
      --arg prompt "$PROMPT" \
      --argjson temp "$TEMPERATURE" \
      '{
        model: $model,
        messages: [
          { role: "user", content: $prompt }
        ],
        temperature: $temp,
        response_format: { type: "json_object" }
      }'
  else
    jq -n \
      --arg model "$MODEL" \
      --arg prompt "$PROMPT" \
      --argjson temp "$TEMPERATURE" \
      '{
        model: $model,
        messages: [
          { role: "user", content: $prompt }
        ],
        temperature: $temp
      }'
  fi
}

# ---- Single request ----
request_once() {
  curl -sS \
    --max-time "$TIMEOUT" \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
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

    build_response "done" "$OUTPUT" "" \
      "$(jq -n --arg endpoint "$ENDPOINT" '{endpoint: $endpoint}')"

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
build_response "error" "HTTP request failed after $RETRIES attempts" "api_error" \
  "$(jq -n --arg endpoint "$ENDPOINT" '{endpoint: $endpoint}')"

adapter_exit