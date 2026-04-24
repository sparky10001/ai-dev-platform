#!/bin/bash
##################################################################
# goose-config.sh — Minimal Goose bootstrap (LiteLLM-native)
#
# Design:
#   - Goose is a thin client
#   - LiteLLM is the ONLY model gateway
#   - Config is idempotent and declarative
##################################################################

set -euo pipefail

echo "🦆 Configuring Goose (LiteLLM-native)..."

# ---- Ensure Goose exists ----
if ! command -v goose >/dev/null 2>&1; then
    echo "⚠️ Goose not installed — skipping"
    exit 0
fi

# ---- Load environment ----
ENV_FILE="$(dirname "$0")/../.env"
[ -f "$ENV_FILE" ] && set -a && source "$ENV_FILE" && set +a

# ---- Required LiteLLM endpoint ----
LITELLM_HOST="${LITELLM_HOST:-http://litellm:4000}"
LITELLM_BASE="${LITELLM_BASE_PATH:-v1/chat/completions}"

BASE_URL="${LITELLM_HOST}/v1"

# ---- Normalize config command ----
GOOSE_CMD=""

if goose config set provider openai >/dev/null 2>&1; then
    GOOSE_CMD="config"
elif goose configure set provider openai >/dev/null 2>&1; then
    GOOSE_CMD="configure"
else
    echo "⚠️ Goose CLI non-interactive mode not supported — skipping"
    exit 0
fi

goose_set() {
    local key="$1"
    local value="$2"

    if [ "$GOOSE_CMD" = "config" ]; then
        goose config set "$key" "$value" 2>/dev/null || true
    else
        goose configure set "$key" "$value" 2>/dev/null || true
    fi
}

# ==============================================================
# 🧠 CORE CONFIG (ONLY THING THAT MATTERS)
# ==============================================================

# Goose always talks to LiteLLM
goose_set provider "openai-compatible"
goose_set base_url "$BASE_URL"

# Optional model hint (LiteLLM handles routing anyway)
if [ -n "${GOOSE_MODEL:-}" ]; then
    goose_set model "$GOOSE_MODEL"
else
    goose_set model "fast"
fi

# Disable any provider-specific assumptions
goose_set temperature "0.7" || true

# ==============================================================
# 📁 Persistence note
# ==============================================================

echo "✅ Goose configured for LiteLLM"
echo "   Endpoint: $BASE_URL"
echo "   Model:    ${GOOSE_MODEL:-fast}"
echo ""
echo "ℹ️ Goose is now a thin client — all routing handled by LiteLLM"