#!/bin/bash
###################################################################
# goose.sh — Production Goose adapter (OpenAI-only, stateless)
###################################################################

set -euo pipefail

GOOSE_BIN=${GOOSE_BIN:-goose}

if ! command -v "$GOOSE_BIN" >/dev/null 2>&1; then
    echo "❌ Goose not installed"
    echo "👉 Install: make install-goose"
    echo "👉 Or switch: make http"
    exit 1
fi

COMMAND=$1
shift || true

# ---- Load env ----
ENV_FILE="$(dirname "$0")/../../.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ---- Enforce supported provider ----
if [ "${MODEL_PROVIDER:-openai}" != "openai" ]; then
    echo "⚠️ Goose adapter only supports MODEL_PROVIDER=openai"
    echo "👉 Switching to http adapter is recommended:"
    echo "   make http"
    exit 1
fi

MODEL="${MODEL_NAME:-gpt-4o-mini}"

# ---- Context ----
CONTEXT=""
if [ -n "${ACTIVE_PROJECT:-}" ]; then
    CONTEXT="[Project: $ACTIVE_PROJECT] "
fi

INPUT="$*"

# ---- Build prompt ----
case "$COMMAND" in
  run)      PROMPT="${CONTEXT}${INPUT}" ;;
  fix)      PROMPT="${CONTEXT}Fix this issue: ${INPUT}" ;;
  explain)  PROMPT="${CONTEXT}Explain this: ${INPUT}" ;;
  refactor) PROMPT="${CONTEXT}Refactor the following: ${INPUT}" ;;
  query)    PROMPT="${CONTEXT}${INPUT}" ;;
  *)
    echo "Usage: goose.sh [run|fix|explain|refactor|query] <args>"
    exit 1
    ;;
esac

# ---- Execute ----
echo "$PROMPT" | "$GOOSE_BIN" run \
    --no-session \
    --provider openai \
    --model "$MODEL" \
    --text -