#!/bin/bash
###################################################################
# ollama.sh — Local LLM Adapter v3.4 (Production Stable)
#
# Goals:
# - Deterministic output contract
# - Safe JSON parsing (never jq-crash)
# - Unified Ollama + OpenAI-compatible support
# - Clean retry semantics
# - Always returns router-safe response
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
RAW_ENDPOINT="${OLLAMA_ENDPOINT:-${MODEL_ENDPOINT:-http://localhost:11434}}"
MODEL="${OLLAMA_MODEL:-tinyllama}"
TIMEOUT="${AI_TIMEOUT:-60}"
RETRIES="${AI_RETRIES:-2}"

# ---------------------------------------------------------------
# Detect API type
# ---------------------------------------------------------------
if [[ "$RAW_ENDPOINT" == *"/v1"* ]]; then
  ENDPOINT_TYPE="openai"
  ENDPOINT="$RAW_ENDPOINT/chat/completions"
else
  ENDPOINT_TYPE="ollama"
  ENDPOINT="$RAW_ENDPOINT/api/generate"
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
# Safe JSON validator
# ---------------------------------------------------------------
is_json_object() {
  echo "$1" | jq -e 'type == "object"' >/dev/null 2>&1
}

# ---------------------------------------------------------------
# Request layer (NO silent failure)
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
# Retry loop (stable)
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
# Hard failure guard
# ---------------------------------------------------------------
if [ -z "$RESPONSE" ]; then
  build_response "error" "No response from Ollama endpoint" "api_error"
  adapter_exit
fi

if ! is_json_object "$RESPONSE"; then
  build_response "error" "Invalid JSON from model" "api_error"
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
# Final guard
# ---------------------------------------------------------------
if [ -z "$OUTPUT" ]; then
  build_response "error" "Empty model response (no extractable content)" "api_error"
  adapter_exit
fi

# ---------------------------------------------------------------
# SUCCESS CONTRACT (CRITICAL)
# ---------------------------------------------------------------
build_response "done" "$OUTPUT" "" \
  "$(jq -n --arg model "$MODEL" --arg endpoint "$ENDPOINT" \
  '{mode:"local", provider:"ollama", model:$model, endpoint:$endpoint}')"

adapter_exit