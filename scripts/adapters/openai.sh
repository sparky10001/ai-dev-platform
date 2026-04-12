#!/bin/bash
###################################################################
# OpenAI-Compatible Adapter (Production Grade)
###################################################################

set -euo pipefail

COMMAND="${1:-}"
shift || true

PROMPT="$*"

# ---- Config defaults ----
MODEL="${MODEL_NAME:-gpt-4o-mini}"
ENDPOINT="${MODEL_ENDPOINT:-http://127.0.0.1:8000/v1}"
API_KEY="${OPENAI_API_KEY:-dummy}"
TEMPERATURE="${MODEL_TEMPERATURE:-0.7}"
MAX_TOKENS="${MODEL_MAX_TOKENS:-512}"
STREAM="${AI_STREAM:-false}"
JSON_MODE="${AI_JSON_MODE:-false}"
RETRIES="${AI_RETRIES:-3}"

if [ -z "$COMMAND" ]; then
    echo "❌ No command provided"
    exit 1
fi

# ---- Build messages ----
SYSTEM_PROMPT="You are a helpful AI assistant."

case "$COMMAND" in
    run)      USER_PROMPT="$PROMPT" ;;
    explain)  USER_PROMPT="Explain clearly:\n$PROMPT" ;;
    fix)      USER_PROMPT="Fix this:\n$PROMPT" ;;
    refactor) USER_PROMPT="Refactor this:\n$PROMPT" ;;
    query)    USER_PROMPT="$PROMPT" ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        exit 1
        ;;
esac

# ---- JSON mode ----
if [ "$JSON_MODE" = "true" ]; then
    RESPONSE_FORMAT='"response_format":{"type":"json_object"},'
else
    RESPONSE_FORMAT=""
fi

# ---- Request payload ----
build_payload() {
cat <<EOF
{
  "model": "$MODEL",
  "temperature": $TEMPERATURE,
  "max_tokens": $MAX_TOKENS,
  $RESPONSE_FORMAT
  "messages": [
    {"role": "system", "content": "$SYSTEM_PROMPT"},
    {"role": "user", "content": "$USER_PROMPT"}
  ]
}
EOF
}

# ---- Streaming handler ----
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

# ---- Standard request ----
request_once() {
    curl -s "$ENDPOINT/chat/completions" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$(build_payload)"
}

# ---- Retry logic ----
attempt=1
while [ $attempt -le $RETRIES ]; do
    if [ "$STREAM" = "true" ]; then
        stream_response && exit 0
    else
        RESPONSE=$(request_once || true)

        if echo "$RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
            echo "$RESPONSE" | jq -r '.choices[0].message.content'
            exit 0
        fi
    fi

    echo "⚠️ Attempt $attempt failed — retrying..."
    sleep $((attempt * 2))
    attempt=$((attempt + 1))
done

echo "❌ OpenAI adapter failed after $RETRIES attempts"
exit 1