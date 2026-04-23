#!/bin/bash
###################################################################
# ollama.sh — Local LLM Adapter v3.5
#
# Fixes from v3.4:
# - Added attempt_with_fallback on all failure paths
#   (was calling build_response + adapter_exit, skipping fallback)
# - No symlinks
###################################################################

set -euo pipefail

ADAPTER_NAME="ollama"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"

source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---------------------------------------------------------------
# Load env
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ---------------------------------------------------------------
# Config
# ---------------------------------------------------------------
RAW_ENDPOINT="${OLLAMA_ENDPOINT:-${MODEL_ENDPOINT:-http://ollama:11434}}"
MODEL="${OLLAMA_MODEL:-tinyllama}"
TIMEOUT="${AI_TIMEOUT:-60}"
RETRIES="${AI_RETRIES:-2}"

# ---------------------------------------------------------------
# Detect API type
# ---------------------------------------------------------------
if [[ "$RAW_ENDPOINT" == *"/v1"* ]]; then
  ENDPOINT_TYPE="openai"
  ENDPOINT="${RAW_ENDPOINT}/chat/completions"
else
  ENDPOINT_TYPE="ollama"
  ENDPOINT="${RAW_ENDPOINT}/api/generate"
fi

# ---------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------
build_prompt() {
  case "$COMMAND" in
    run)      echo "$INPUT" ;;
    fix)      echo "Fix this:\n$INPUT" ;;
    explain)  echo "Explain:\n$INPUT" ;;
    refactor) echo "Refactor:\n$INPUT" ;;
    *)        echo "$INPUT" ;;
  esac
}

PROMPT="$(build_prompt)"

# ---------------------------------------------------------------
# Validate command
# ---------------------------------------------------------------
if [ -z "$COMMAND" ]; then
  build_response "error" "Missing command" "invalid_request"
  adapter_exit
fi

# ---------------------------------------------------------------
# Safe JSON validator
# ---------------------------------------------------------------
is_json_object() {
  echo "$1" | jq -e 'type == "object"' >/dev/null 2>&1
}

# ---------------------------------------------------------------
# Request layer
# ---------------------------------------------------------------
request_once() {
  if [ "$ENDPOINT_TYPE" = "openai" ]; then
    curl -sS --max-time "$TIMEOUT" -X POST "$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg model "$MODEL" \
        --arg prompt "$PROMPT" \
        '{
          model: $model,
          messages: [{role:"user", content:$prompt}]
        }')" 2>/dev/null
  else
    curl -sS --max-time "$TIMEOUT" -X POST "$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "$(jq -n \
        --arg model "$MODEL" \
        --arg prompt "$PROMPT" \
        '{
          model: $model,
          prompt: $prompt,
          stream: false
        }')" 2>/dev/null
  fi
}

# ---------------------------------------------------------------
# Retry loop
# ---------------------------------------------------------------
attempt=1
RESPONSE=""

while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once || true)"

  if [ -n "$RESPONSE" ] && echo "$RESPONSE" | jq empty >/dev/null 2>&1; then
    break
  fi

  RESPONSE=""
  sleep "$attempt"
  attempt=$((attempt + 1))

done

# ---------------------------------------------------------------
# Failure guards — NOW WITH FALLBACK (fix from v3.4)
# ---------------------------------------------------------------
if [ -z "$RESPONSE" ]; then
  attempt_with_fallback "$PROMPT" "ollama_no_response"
  adapter_exit
fi

if ! is_json_object "$RESPONSE"; then
  attempt_with_fallback "$PROMPT" "ollama_invalid_json"
  adapter_exit
fi

# ---------------------------------------------------------------
# Unified output extraction (multi-format safe)
# ---------------------------------------------------------------
OUTPUT=$(echo "$RESPONSE" | jq -r '
  .response //
  .message.content //
  .choices[0].message.content //
  .output //
  empty
')

# ---------------------------------------------------------------
# Empty output guard — NOW WITH FALLBACK (fix from v3.4)
# ---------------------------------------------------------------
if [ -z "$OUTPUT" ]; then
  attempt_with_fallback "$PROMPT" "ollama_empty_output"
  adapter_exit
fi

# ---------------------------------------------------------------
# SUCCESS CONTRACT
# ---------------------------------------------------------------
build_response "done" "$OUTPUT" "" \
  "$(jq -n \
    --arg model "$MODEL" \
    --arg endpoint "$ENDPOINT" \
    --arg type "$ENDPOINT_TYPE" \
    '{mode:"local", provider:"ollama", model:$model, endpoint:$endpoint, api_type:$type}')"

adapter_exit
