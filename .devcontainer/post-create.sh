#!/usr/bin/env bash
##################################################################
# post-create.sh — Dev Container post-creation setup
##################################################################

set -e
set -o pipefail

echo ""
echo "🚀 AI Dev Platform — Environment Setup"
echo "======================================="

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

# ---- Python virtual environment ----
VENV_PATH="/opt/venv"
if [ -d "$VENV_PATH" ]; then
    echo ""
    echo "🐍 Activating Python virtual environment..."
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment active: $(which python)"
    echo "🔧 Installing/updating Python packages..."
    pip install --upgrade pip
    pip install --upgrade requests python-dotenv httpx
    echo "✅ Python packages ready: $(python --version)"
else
    echo "⚠️ Virtual environment not found at $VENV_PATH — skipping Python setup"
fi

# ---- Node.js dependencies ----
if [ -f "$ROOT_DIR/package.json" ]; then
    echo ""
    echo "📦 Installing Node.js dependencies..."
    npm install
    echo "✅ Node.js packages installed"
fi

# ---- Make setup ----
if [ -f "$ROOT_DIR/Makefile" ]; then
    echo ""
    echo "🛠 Running make setup..."
    make setup
    echo "✅ Make setup complete"
fi

# ---- Adapter symlink ----
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

# ---- Goose CLI configuration ----
echo ""
echo "🔧 Configuring AI provider: $MODEL_PROVIDER"
if [ -f "$SCRIPT_DIR/goose-config.sh" ]; then
    bash "$SCRIPT_DIR/goose-config.sh" || echo "⚠️ Goose config skipped"
else
    echo "⚠️ Goose config script not found — skipping"
fi

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