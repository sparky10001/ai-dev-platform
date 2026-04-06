#!/bin/bash
###################################################################
# post-create.sh — Dev Container post-creation setup
#
# Runs automatically when the Dev Container is created.
# Sets up the full AI Dev Platform environment.
###################################################################

set -e

echo ""
echo "🚀 AI Dev Platform — Environment Setup"
echo "======================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---- Permissions ----
echo "🔧 Setting permissions..."
chmod +x "$ROOT_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$ROOT_DIR/scripts/adapters/"*.sh 2>/dev/null || true
echo "✅ Permissions set"

# ---- Environment file ----
echo ""
echo "🔧 Setting up environment..."
if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "✅ Created .env from template"
    echo "   ⚠️  Edit .env to configure your provider"
else
    echo "✅ .env already exists"
fi

# ---- Load environment ----
export $(grep -v '^#' "$ROOT_DIR/.env" | xargs) 2>/dev/null || true

# ---- Set defaults ----
MODEL_PROVIDER=${MODEL_PROVIDER:-openai}
AI_ADAPTER=${AI_ADAPTER:-goose}

# ---- Set active adapter symlink ----
echo ""
echo "🔧 Configuring adapter: $AI_ADAPTER"
ADAPTERS_DIR="$ROOT_DIR/scripts/adapters"

if [ -f "$ADAPTERS_DIR/${AI_ADAPTER}.sh" ]; then
    ln -sf "$ADAPTERS_DIR/${AI_ADAPTER}.sh" "$ADAPTERS_DIR/ai.sh"
    echo "✅ Adapter symlink → ${AI_ADAPTER}.sh"
else
    echo "⚠️  Adapter not found: ${AI_ADAPTER}.sh — defaulting to mock"
    ln -sf "$ADAPTERS_DIR/mock.sh" "$ADAPTERS_DIR/ai.sh"
fi

# ---- Configure Goose ----
echo ""
echo "🔧 Configuring AI provider: $MODEL_PROVIDER"
bash "$SCRIPT_DIR/goose-config.sh" || true

# ---- Summary ----
echo ""
echo "======================================="
echo "✅ AI Dev Platform ready!"
echo ""
echo "   Provider:  $MODEL_PROVIDER"
echo "   Adapter:   $AI_ADAPTER"
echo "   Endpoint:  ${MODEL_ENDPOINT:-default}"
echo "   Project:   ${ACTIVE_PROJECT:-not set}"
echo ""
echo "   Quick start:"
echo "     make help          — show all commands"
echo "     make health        — check system health"
echo "     make status        — show active config"
echo "     make openai        — switch to OpenAI"
echo "     make local         — switch to local Ollama"
echo "     make mock          — offline/plane mode"
echo ""
