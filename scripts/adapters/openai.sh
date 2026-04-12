#!/bin/bash
###################################################################
# openai.sh — Contract-Based OpenAI Adapter (Production)
#
# Features:
# - JSON contract output (runtime v3 compatible)
# - Retries with backoff
# - Streaming support (optional)
# - JSON mode support
# - OpenAI-compatible endpoints
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Load env safely ----
ENV_FILE="$(dirname "$0")/../../.env"
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
STREAM="${AI_STREAM:-false}"
JSON_MODE="${AI_JSON_MODE:-false}"
RETRIES="${AI_RETRIES:-3}"

# ---- Validate ----
if [ -z "$COMMAND" ]; then
    echo '{"status":"error","output":"No command provided","next_input":null}'
    exit 1
fi

if [ -z "$API_KEY" ] && [[ "$ENDPOINT" == *"openai.com"* ]]; then
    echo '{"status":"error","output":"Missing OPENAI_API_KEY","next_input":null}'
    exit 1
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
    echo '{"status":"error","output":"Unknown command","next_input":null}'
    exit 1
    ;;
esac

# ---- JSON escape ----
escape_json() {
  printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

ESCAPED_PROMPT=$(escape_json "$PROMPT")

# ---- JSON mode ----
if [ "$JSON_MODE" = "true" ]; then
  RESPONSE_FORMAT='"response_format":{"type":"json_object"},'
else
  RESPONSE_FORMAT=""
fi

# ---- Payload ----
build_payload() {
cat <<EOF
{
  "model": "$MODEL",
  "temperature": $TEMPERATURE,
  "max_tokens": $MAX_TOKENS,
  $RESPONSE_FORMAT
  "messages": [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": $ESCAPED_PROMPT}
  ]
}
EOF
}

# ---- Contract builder ----
build_response() {
  local status="$1"
  local output="$2"

  jq -n \
    --arg status "$status" \
    --arg output "$output" \
    '{
      status: $status,
      output: $output,
      next_input: null,
      tool_call: null,
      meta: {
        adapter: "openai",
        model: "'$MODEL'",
        endpoint: "'$ENDPOINT'",
        timestamp: (now | todate)
      }
    }'
}

# ---- Streaming ----
stream_response() {
  curl -sN "$ENDPOINT/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(build_payload | jq '. + {stream: true}')" \
  | while read -r line; do
      if [[ "$line" == data:* ]]; then
          chunk=$(echo "$line" | sed 's/^data: //')
          [ "$chunk" = "[DONE]" ] && break
          echo "$chunk" | jq -r '.choices[0].delta.content // ""'
      fi
  done
}

# ---- Single request ----
request_once() {
  curl -s "$ENDPOINT/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(build_payload)"
}

# ---- Retry loop ----
attempt=1
while [ $attempt -le $RETRIES ]; do

  if [ "$STREAM" = "true" ]; then
    OUTPUT=$(stream_response || true)

    if [ -n "$OUTPUT" ]; then
      build_response "done" "$OUTPUT"
      exit 0
    fi

  else
    RESPONSE=$(request_once || true)

    if echo "$RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
      OUTPUT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')
      build_response "done" "$OUTPUT"
      exit 0
    fi
  fi

  sleep $((attempt * 2))
  attempt=$((attempt + 1))
done

# ---- Failure ----
build_response "error" "OpenAI request failed after $RETRIES attempts"
exit 1