#!/bin/bash
###################################################################
# http-agent.sh — Contract-based HTTP AI adapter
#
# Dependency-light (curl + jq)
# OpenAI-compatible API
# Fully aligned with runtime contract
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Load env safely ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"

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

CONTEXT=""
[ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

# ---- Validate ----
if [ -z "$COMMAND" ]; then
    jq -n '{
      status: "error",
      output: "Missing command",
      next_input: null,
      tool_call: null,
      meta: { adapter: "http-agent" }
    }'
    exit 1
fi

# ---- Prompt builder ----
case "$COMMAND" in
  run)      PROMPT="${CONTEXT}${INPUT}" ;;
  fix)      PROMPT="${CONTEXT}Fix this issue: ${INPUT}" ;;
  explain)  PROMPT="${CONTEXT}Explain this: ${INPUT}" ;;
  refactor) PROMPT="${CONTEXT}Refactor: ${INPUT}" ;;
  query)    PROMPT="${CONTEXT}${INPUT}" ;;
  *)
    jq -n --arg cmd "$COMMAND" '{
      status: "error",
      output: ("Unknown command: " + $cmd),
      next_input: null,
      tool_call: null,
      meta: { adapter: "http-agent" }
    }'
    exit 1
    ;;
esac

# ---- Build request body safely ----
BODY=$(jq -n \
  --arg model "$MODEL" \
  --arg content "$PROMPT" \
  --argjson temp "$TEMPERATURE" \
  '{
    model: $model,
    messages: [
      { role: "user", content: $content }
    ],
    temperature: $temp
  }')

# Optional JSON mode
if [ "$JSON_MODE" = "true" ]; then
  BODY=$(echo "$BODY" | jq '. + {response_format: {type: "json_object"}}')
fi

# ---- Request loop ----
COUNT=0
RESPONSE=""

while [ "$COUNT" -lt "$RETRIES" ]; do

  RESPONSE=$(curl -s \
    --max-time "$TIMEOUT" \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
    -d "$BODY" || true)

  if echo "$RESPONSE" | jq -e '.choices' >/dev/null 2>&1; then
      break
  fi

  COUNT=$((COUNT + 1))
  sleep 1
done

# ---- Failure ----
if ! echo "$RESPONSE" | jq -e '.choices' >/dev/null 2>&1; then
  jq -n \
    --arg err "API request failed after ${RETRIES} attempts" \
    --arg resp "$RESPONSE" \
    '{
      status: "error",
      output: ($err + "\n" + $resp),
      next_input: null,
      tool_call: null,
      meta: {
        adapter: "http-agent",
        endpoint: "failed"
      }
    }'
  exit 1
fi

# ---- Extract content safely ----
CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')

# ---- Emit contract ----
jq -n \
  --arg output "$CONTENT" \
  '{
    status: "done",
    output: $output,
    next_input: null,
    tool_call: null,
    meta: {
      adapter: "http-agent",
      mode: "http",
      timestamp: (now | todate)
    }
  }'