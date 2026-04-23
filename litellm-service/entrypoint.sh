#!/bin/bash
###################################################################
# entrypoint.sh — LiteLLM service entrypoint
#
# Responsibilities:
# - Validate config exists
# - Wait for Ollama to be ready (dependency)
# - Start LiteLLM proxy server
###################################################################

set -e

LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_CONFIG="${LITELLM_CONFIG:-/app/config.yaml}"
OLLAMA_BASE="${OLLAMA_BASE_URL:-http://ollama:11434}"
MAX_WAIT="${LITELLM_STARTUP_WAIT:-120}"

echo ""
echo "🔀 LiteLLM Router Starting"
echo "=========================="
echo "   Port:    $LITELLM_PORT"
echo "   Config:  $LITELLM_CONFIG"
echo "   Ollama:  $OLLAMA_BASE"
echo "   Model:   ${ACTIVE_MODEL:-fast}"
echo ""

# ---- Validate config ----
if [ ! -f "$LITELLM_CONFIG" ]; then
    echo "❌ Config not found: $LITELLM_CONFIG"
    exit 1
fi

echo "✅ Config found: $LITELLM_CONFIG"

# ---- Wait for Ollama ----
echo "⏳ Waiting for Ollama to be ready..."
elapsed=0

while [ "$elapsed" -lt "$MAX_WAIT" ]; do
    if curl -sf "${OLLAMA_BASE}/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama ready (${elapsed}s)"
        break
    fi
    printf "\r   ⏳ Waiting for Ollama... (%ds)" "$elapsed"
    sleep 3
    elapsed=$((elapsed + 3))
done

if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo ""
    echo "⚠️  Ollama not ready after ${MAX_WAIT}s — starting anyway"
    echo "   LiteLLM will retry connections as requests arrive"
fi

echo ""
echo "🚀 Starting LiteLLM proxy..."
echo "   Endpoint: http://0.0.0.0:${LITELLM_PORT}"
echo "   API:      http://0.0.0.0:${LITELLM_PORT}/v1/chat/completions"
echo ""

# ---- Start LiteLLM ----
exec litellm \
    --config "$LITELLM_CONFIG" \
    --port "$LITELLM_PORT" \
    --host "0.0.0.0" \
