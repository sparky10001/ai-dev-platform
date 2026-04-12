#!/bin/bash
###################################################################
# goose.sh — Contract-based Goose Adapter (production)
#
# Stateless, CI-safe, no interactive config
# Fully compatible with runtime v3 contract
###################################################################

set -euo pipefail

GOOSE_BIN="${GOOSE_BIN:-goose}"

# ---- Validate Goose ----
if ! command -v "$GOOSE_BIN" >/dev/null 2>&1; then
    echo '{
      "status": "error",
      "output": "Goose not installed",
      "next_input": null,
      "tool_call": null,
      "meta": { "adapter": "goose" }
    }'
    exit 0
fi

COMMAND="${1:-}"
shift || true

INPUT="$*"

# ---- Load env ----
ENV_FILE="$(dirname "$0")/../../.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ---- Validate provider ----
if [ "${MODEL_PROVIDER:-openai}" != "openai" ]; then
    echo '{
      "status": "error",
      "output": "Goose only supports MODEL_PROVIDER=openai",
      "next_input": null,
      "tool_call": null,
      "meta": { "adapter": "goose" }
    }'
    exit 0
fi

MODEL="${MODEL_NAME:-gpt-4o-mini}"
RETRIES="${AI_RETRIES:-2}"

# ---- Context ----
CONTEXT=""
[ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

# ---- Build prompt ----
case "$COMMAND" in
  run)      PROMPT="${CONTEXT}${INPUT}" ;;
  fix)      PROMPT="${CONTEXT}Fix this issue: ${INPUT}" ;;
  explain)  PROMPT="${CONTEXT}Explain this: ${INPUT}" ;;
  refactor) PROMPT="${CONTEXT}Refactor the following: ${INPUT}" ;;
  query)    PROMPT="${CONTEXT}${INPUT}" ;;
  *)
    PROMPT="${CONTEXT}${INPUT}"
    ;;
esac

# ---- Retry loop ----
ATTEMPT=1
RESPONSE=""

while [ "$ATTEMPT" -le "$RETRIES" ]; do

    RESPONSE=$(echo "$PROMPT" | "$GOOSE_BIN" run \
        --no-session \
        --provider openai \
        --model "$MODEL" \
        --text - 2>/dev/null || true)

    if [ -n "$RESPONSE" ]; then
        break
    fi

    sleep $ATTEMPT
    ATTEMPT=$((ATTEMPT + 1))
done

# ---- Handle failure ----
if [ -z "$RESPONSE" ]; then
    jq -n \
      --arg msg "Goose failed after $RETRIES attempts" \
      '{
        status: "error",
        output: $msg,
        next_input: null,
        tool_call: null,
        meta: {
          adapter: "goose",
          retries: '"$RETRIES"'
        }
      }'
    exit 0
fi

# ---- Emit contract JSON ----
jq -n \
  --arg output "$RESPONSE" \
  --arg model "$MODEL" \
  '{
    status: "done",
    output: $output,
    next_input: null,
    tool_call: null,
    meta: {
      adapter: "goose",
      model: $model,
      mode: "cli",
      timestamp: (now | todate)
    }
  }'