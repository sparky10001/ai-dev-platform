#!/bin/bash
###################################################################
# goose.sh — Goose AI agent adapter
#
# Stable interface — swap this file to change AI providers
# All commands mirror mock.sh exactly
###################################################################

COMMAND=$1
shift

# ---- Load environment ----
ENV_FILE="$(dirname "$0")/../../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Validate Goose is available ----
if ! command -v goose &> /dev/null; then
    echo "❌ Goose not installed"
    echo "   Install: https://block.github.io/goose/docs/getting-started/installation"
    echo "   Or switch to mock: make mock"
    exit 1
fi

# ---- Add project context if set ----
CONTEXT=""
if [ -n "$ACTIVE_PROJECT" ]; then
    CONTEXT="[Project: $ACTIVE_PROJECT] "
fi

case "$COMMAND" in
  run)
    goose run "${CONTEXT}$@"
    ;;

  explain)
    goose prompt "${CONTEXT}Explain this: $@"
    ;;

  refactor)
    goose run "${CONTEXT}Refactor the following: $@"
    ;;

  fix)
    goose run "${CONTEXT}Fix this issue: $@"
    ;;

  query)
    goose prompt "${CONTEXT}$@"
    ;;

  "")
    echo "Usage: goose.sh [run|explain|refactor|fix|query] <args>"
    ;;

  *)
    echo "Unknown command: $COMMAND"
    echo "Usage: goose.sh [run|explain|refactor|fix|query] <args>"
    exit 1
    ;;
esac
