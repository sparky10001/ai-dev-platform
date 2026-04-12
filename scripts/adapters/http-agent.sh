#!/bin/bash
# http-agent.sh — dependency-free HTTP adapter (production-safe)

set -e

COMMAND=$1
shift

# Load env safely
set -a
[ -f .env ] && source .env
set +a

ENDPOINT="${MODEL_ENDPOINT:-http://localhost:8000/v1}"
MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-3}"

CONTEXT=""
[ -n "$ACTIVE_PROJECT" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

case "$COMMAND" in
  run)      PROMPT="${CONTEXT}$*" ;;
  fix)      PROMPT="${CONTEXT}Fix this issue: $*" ;;
  explain)  PROMPT="${CONTEXT}Explain this: $*" ;;
  refactor) PROMPT="${CONTEXT}Refactor: $*" ;;
  query)    PROMPT="${CONTEXT}$*" ;;
  *)        echo "Unknown command: $COMMAND"; exit 1 ;;
esac

# Escape JSON safely (no python/jq)
ESCAPED_PROMPT=$(printf '%s' "$PROMPT" \
  | sed 's/"/\\"/g' \
  | sed ':a;N;$!ba;s/\n/\\n/g')

BODY=$(cat <<EOF
{
  "model": "$MODEL",
  "messages": [
    {"role": "user", "content": "$ESCAPED_PROMPT"}
  ]
}
EOF
)

COUNT=0
RESPONSE=""

while [ $COUNT -lt $RETRIES ]; do
  RESPONSE=$(curl -s \
    -X POST "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${OPENAI_API_KEY:-}" \
    -d "$BODY")

  echo "$RESPONSE" | grep -q "choices" && break

  COUNT=$((COUNT+1))
  sleep 1
done

if ! echo "$RESPONSE" | grep -q "choices"; then
  echo "❌ API request failed after $RETRIES attempts"
  echo "$RESPONSE"
  exit 1
fi

# Extract content (best-effort without jq)
echo "$RESPONSE" \
  | sed -n 's/.*"content":"\([^"]*\)".*/\1/p' \
  | sed 's/\\n/\n/g'