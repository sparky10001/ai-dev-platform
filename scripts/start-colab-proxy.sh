#!/bin/bash
###################################################################
# start-colab-proxy.sh — Configure Google Colab GPU proxy
#
# Usage:
#   ./scripts/start-colab-proxy.sh
#   ./scripts/start-colab-proxy.sh https://your-ngrok-url.ngrok.io
#
# Colab Setup Instructions:
#   1. Open a Colab notebook with GPU runtime
#   2. Run the LiteLLM proxy cell (see docs/setup.md)
#   3. Copy the ngrok URL and paste here
###################################################################

set -e

ENV_FILE="$(dirname "$0")/../.env"

echo ""
echo "📡 Colab GPU Proxy Setup"
echo "========================"
echo ""
echo "Before continuing, ensure:"
echo "  1. Your Colab notebook is running with GPU runtime"
echo "  2. LiteLLM proxy cell is running"
echo "  3. You have your ngrok URL ready"
echo ""

# ---- Accept URL as arg or prompt ----
if [ -n "$1" ]; then
    COLAB_URL=$1
    echo "✅ Using provided URL: $COLAB_URL"
else
    read -rp "📋 Paste your Colab ngrok URL: " COLAB_URL
fi

# ---- Validate ----
if [ -z "$COLAB_URL" ]; then
    echo "❌ No URL provided — exiting"
    exit 1
fi

# Strip trailing slash
COLAB_URL="${COLAB_URL%/}"

# ---- Test connectivity ----
echo ""
echo "🔍 Testing connection to $COLAB_URL..."

if curl -sf "${COLAB_URL}/health" --max-time 5 > /dev/null 2>&1; then
    echo "✅ Colab proxy is reachable!"
elif curl -sf "${COLAB_URL}" --max-time 5 > /dev/null 2>&1; then
    echo "✅ Colab URL is reachable (no /health endpoint)"
else
    echo "⚠️  Could not reach $COLAB_URL — continuing anyway"
    echo "   Check your Colab notebook is still running"
fi

# ---- Update .env ----
update_env() {
    local key=$1
    local val=$2
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

update_env "COLAB_URL" "$COLAB_URL"
update_env "MODEL_ENDPOINT" "${COLAB_URL}/v1"
update_env "MODEL_PROVIDER" "colab"

echo ""
echo "✅ Colab proxy configured!"
echo "   URL:      $COLAB_URL"
echo "   Endpoint: ${COLAB_URL}/v1"
echo ""
echo "   Now run: make colab"
echo ""
