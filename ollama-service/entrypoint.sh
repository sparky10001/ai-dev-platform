#!/bin/bash
###################################################################
# entrypoint.sh — Ollama service entrypoint
#
# Responsibilities:
# - Start Ollama server in background
# - Wait for server to be ready
# - Pull required models if not already present
# - Keep container alive with server in foreground
###################################################################

set -e

DEFAULT_MODEL="${DEFAULT_MODEL:-tinyllama}"
EXTRA_MODELS="${EXTRA_MODELS:-}"
MAX_WAIT="${OLLAMA_STARTUP_WAIT:-60}"

echo ""
echo "🦙 Ollama Service Starting"
echo "=========================="
echo "   Model:    $DEFAULT_MODEL"
echo "   Host:     ${OLLAMA_HOST:-0.0.0.0}"
echo "   Port:     11434"
echo ""

# ---- Start Ollama server in background ----
echo "🚀 Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# ---- Wait for server to be ready ----
echo "⏳ Waiting for Ollama server to be ready..."
elapsed=0

while [ "$elapsed" -lt "$MAX_WAIT" ]; do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama server ready (${elapsed}s)"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ "$elapsed" -ge "$MAX_WAIT" ]; then
    echo "❌ Ollama server failed to start after ${MAX_WAIT}s"
    exit 1
fi

# ---- Pull model function ----
pull_model() {
    local model="$1"

    # Check if already present
    if ollama list 2>/dev/null | grep -q "^${model}"; then
        echo "✅ Model already present: $model"
        return 0
    fi

    echo "📥 Pulling model: $model"
    if ollama pull "$model"; then
        echo "✅ Model ready: $model"
    else
        echo "⚠️  Failed to pull model: $model"
        return 1
    fi
}

# ---- Pull default model ----
pull_model "$DEFAULT_MODEL"

# ---- Pull extra models if specified ----
# EXTRA_MODELS="phi3,llama3.2" — comma separated
if [ -n "$EXTRA_MODELS" ]; then
    IFS=',' read -ra MODELS <<< "$EXTRA_MODELS"
    for model in "${MODELS[@]}"; do
        model=$(echo "$model" | tr -d ' ')
        [ -n "$model" ] && pull_model "$model"
    done
fi

# ---- List available models ----
echo ""
echo "📋 Available models:"
ollama list
echo ""
echo "🎯 Ollama service ready!"
echo "   Endpoint: http://localhost:11434"
echo "   API:      http://localhost:11434/api/generate"
echo "   OpenAI:   http://localhost:11434/v1/chat/completions"
echo ""

# ---- Keep server running (bring to foreground) ----
wait $OLLAMA_PID
