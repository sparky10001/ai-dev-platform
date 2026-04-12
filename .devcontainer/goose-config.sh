#!/bin/bash
##################################################################
# goose-config.sh — Configure Goose AI agent (resilient + optional)
#
# Called by:
#   - post-create.sh
#   - switch-model.sh
#
# Design:
#   - Goose is OPTIONAL
#   - Config is BEST-EFFORT (never breaks pipeline)
#   - Protocol-driven (not provider-name driven)
##################################################################

set -e

echo "🦆 Configuring Goose..."

# ---- Validate Goose is installed ----
if ! command -v goose >/dev/null 2>&1; then
    echo "⚠️  Goose not installed — skipping configuration"
    echo "   Install: make install-goose"
    exit 0
fi

# ---- Load .env ----
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# ---- Detect Goose CLI capabilities ----
GOOSE_CONFIG_CMD=""

if goose config set provider test >/dev/null 2>&1; then
    GOOSE_CONFIG_CMD="config"
elif goose configure set provider test >/dev/null 2>&1; then
    GOOSE_CONFIG_CMD="configure"
else
    GOOSE_CONFIG_CMD="unsupported"
fi

# ---- Wrapper for safe config calls ----
goose_set() {
    local key="$1"
    local value="$2"

    if [ "$GOOSE_CONFIG_CMD" = "config" ]; then
        goose config set "$key" "$value" 2>/dev/null || return 1
    elif [ "$GOOSE_CONFIG_CMD" = "configure" ]; then
        goose configure set "$key" "$value" 2>/dev/null || return 1
    else
        return 1
    fi
}

# ---- Configure based on provider ----
PROVIDER="${MODEL_PROVIDER:-openai}"

case "$PROVIDER" in

  mock)
    echo "✅ Goose → mock mode (no configuration needed)"
    ;;

  openai)
    if goose_set provider openai; then
        goose_set base_url "https://api.openai.com/v1" || true

        if [ -n "$GOOSE_MODEL" ]; then
            goose_set model "$GOOSE_MODEL" || true
        fi

        echo "✅ Goose → OpenAI"
    else
        echo "⚠️  Goose CLI does not support non-interactive config"
        echo "   Run manually: goose configure"
    fi
    ;;

  *)
    # Treat everything else as OpenAI-compatible
    if [ -z "$MODEL_ENDPOINT" ]; then
        echo "❌ MODEL_ENDPOINT required for provider: $PROVIDER"
        exit 1
    fi

    if goose_set provider openai-compatible; then
        goose_set base_url "$MODEL_ENDPOINT" || true

        if [ -n "$GOOSE_MODEL" ]; then
            goose_set model "$GOOSE_MODEL" || true
        fi

        echo "✅ Goose → ${PROVIDER} (${MODEL_ENDPOINT})"
    else
        echo "⚠️  Goose CLI does not support non-interactive config"
        echo "   Run manually: goose configure"
    fi
    ;;

esac

# ---- Project context (informational only) ----
if [ -n "$ACTIVE_PROJECT" ]; then
    echo "📁 Active project context: $ACTIVE_PROJECT"
fi

echo "✅ Goose configuration step complete"