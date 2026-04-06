#!/bin/bash
###################################################################
# goose-config.sh — Configure Goose AI agent
#
# Called automatically by:
#   - post-create.sh (on container creation)
#   - switch-model.sh (on provider switch)
#
# Reads from environment variables set in .env
###################################################################

echo "🦆 Configuring Goose..."

# ---- Validate Goose is installed ----
if ! command -v goose &> /dev/null; then
    echo "⚠️  Goose not installed — skipping configuration"
    echo "   Install: https://block.github.io/goose/docs/getting-started/installation"
    exit 0
fi

# ---- Load .env if not already loaded ----
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Configure based on provider ----
case "${MODEL_PROVIDER:-openai}" in
  openai)
    goose config set provider openai
    goose config set base_url "https://api.openai.com/v1"

    if [ -n "$GOOSE_MODEL" ]; then
        goose config set model "$GOOSE_MODEL"
    fi

    echo "✅ Goose → OpenAI"
    ;;

  colab|local)
    if [ -z "$MODEL_ENDPOINT" ]; then
        echo "❌ MODEL_ENDPOINT required for $MODEL_PROVIDER provider"
        exit 1
    fi

    goose config set provider openai-compatible
    goose config set base_url "$MODEL_ENDPOINT"

    if [ -n "$GOOSE_MODEL" ]; then
        goose config set model "$GOOSE_MODEL"
    fi

    echo "✅ Goose → $MODEL_PROVIDER ($MODEL_ENDPOINT)"
    ;;

  mock)
    echo "✅ Goose → mock mode (no configuration needed)"
    ;;

  *)
    echo "❌ Unknown provider: $MODEL_PROVIDER"
    exit 1
    ;;
esac

# ---- Set project context if available ----
if [ -n "$ACTIVE_PROJECT" ]; then
    echo "📁 Active project context: $ACTIVE_PROJECT"
fi

echo "✅ Goose configured"
