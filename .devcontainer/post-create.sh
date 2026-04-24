#!/usr/bin/env bash
###################################################################
# post-create.sh — Dev Container post-creation setup (v2.2)
#
# Changes from v2.01:
#   - Removed Ollama section wrapped as non-fatal function
###################################################################

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
set -a
source "$ROOT_DIR/.env" 2>/dev/null || true
set +a

# ---- Set defaults ----
MODEL_PROVIDER=${MODEL_PROVIDER:-ollama}
AI_ADAPTER=${AI_ADAPTER:-ollama}

# ---- Python virtual environment ----
VENV_PATH="/opt/venv"
if [ -d "$VENV_PATH" ]; then
    echo ""
    echo "🐍 Activating Python virtual environment..."
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment active: $(which python)"
    echo "🔧 Installing/updating Python packages..."
    pip install --upgrade pip -q
    pip install --upgrade requests python-dotenv httpx fastapi pydantic uvicorn -q
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
    make -C "$ROOT_DIR" setup
    echo "✅ Make setup complete"
fi

# ---- Goose CLI configuration (idempotent bootstrap) ----
echo ""
echo "🔧 Checking Goose configuration..."

GOOSE_CONFIG="$HOME/.config/goose/config.yaml"
WORKSPACE_CONFIG="$ROOT_DIR/.config/goose/config.yaml"

# Ensure persistent config exists
if [ ! -f "$WORKSPACE_CONFIG" ]; then
    echo "⚠️ No persisted Goose config found — running initial setup..."

    if [ -f "$SCRIPT_DIR/goose-config.sh" ]; then
        bash "$SCRIPT_DIR/goose-config.sh" || echo "⚠️ Goose config setup failed"
    else
        echo "⚠️ goose-config.sh not found — skipping initial setup"
    fi
else
    echo "✅ Using persisted Goose config"
fi

# ================================================================
# ✅ SUMMARY
# ================================================================

echo ""
echo "======================================="
echo "✅ AI Dev Platform ready!"
echo ""
echo "   Provider:  $MODEL_PROVIDER"
echo "   Adapter:   $AI_ADAPTER"
echo "   Endpoint:  ${OLLAMA_ENDPOINT:-http://ollama:11434}"
echo "   Model:     ${OLLAMA_MODEL:-tinyllama}"
echo "   Project:   ${ACTIVE_PROJECT:-not set}"
echo ""
echo "   Quick start:"
echo "     ./ai run 'hello'   — test full chain"
echo "     make help          — show all commands"
echo "     make health        — check system health"
echo "     make status        — show active config"
echo "     make validate      — run validation ladder"
echo ""
echo "   Switch provider:"
echo "     ./scripts/switch-model.sh ollama   — local Ollama (default)"
echo "     ./scripts/switch-model.sh mock     — offline/plane mode"
echo "     ./scripts/switch-model.sh openai   — OpenAI API"
echo ""
