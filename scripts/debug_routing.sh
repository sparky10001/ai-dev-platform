#!/bin/bash
set -euo pipefail

BASE_URL="${LITELLM_BASE_URL:-http://litellm:4000/v1}"
KEY="${LITELLM_MASTER_KEY:-ai-dev-platform}"

echo "🔍 Routing Debug"
echo "================"

RESPONSE=$(curl -s -D - \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "balanced",
    "messages": [{"role":"user","content":"ping"}],
    "temperature": 0
  }' \
  "$BASE_URL/chat/completions"
)

# Split headers and body
HEADERS=$(echo "$RESPONSE" | sed -n '1,/^\r$/p')
BODY=$(echo "$RESPONSE" | sed '1,/^\r$/d')

PROVIDER=$(echo "$HEADERS" | grep -i "x-litellm-provider" | awk '{print $2}' | tr -d '\r')
MODEL=$(echo "$HEADERS" | grep -i "x-litellm-model" | awk '{print $2}' | tr -d '\r')

echo "Tier:       balanced"
echo "Provider:   ${PROVIDER:-unknown}"
echo "Model:      ${MODEL:-unknown}"

# Optional latency
LATENCY=$(echo "$HEADERS" | grep -i "x-process-time" | awk '{print $2}' | tr -d '\r')
[ -n "$LATENCY" ] && echo "Latency:    ${LATENCY}s"