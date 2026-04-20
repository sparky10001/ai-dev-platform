#!/usr/bin/env bash
###################################################################
# post-create.sh — Dev Container post-creation setup (v2.0)
#
# New in v2.0:
#   - Ollama service auto-start via docker compose
#   - Waits for tinyllama to be ready before completing
#   - Supports OLLAMA_IMAGE build arg (full vs alpine)
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

# ---- Goose CLI configuration ----
echo ""
echo "🔧 Configuring AI provider: $MODEL_PROVIDER"
if [ -f "$SCRIPT_DIR/goose-config.sh" ]; then
    bash "$SCRIPT_DIR/goose-config.sh" || echo "⚠️ Goose config skipped"
else
    echo "⚠️ Goose config script not found — skipping"
fi

# ================================================================
# 🦙 OLLAMA SERVICE (NEW in v2.0)
# ================================================================

OLLAMA_DIR="$ROOT_DIR/ollama-service"
OLLAMA_ENDPOINT="${OLLAMA_ENDPOINT:-http://host.docker.internal:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-tinyllama}"

echo ""
echo "🦙 Setting up Ollama service..."

# ---- Check if Docker is available ----
if ! command -v docker > /dev/null 2>&1; then
    echo "⚠️  Docker CLI not found — skipping Ollama auto-start"
    echo "   Install Docker CLI or start Ollama manually"
    echo "   cd ollama-service && make up"
else

    # ---- Check if Ollama is already running ----
    if curl -sf "${OLLAMA_ENDPOINT}/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama already running at $OLLAMA_ENDPOINT"

    # ---- Start Ollama service via docker compose ----
    elif [ -f "$OLLAMA_DIR/docker-compose.yml" ]; then
        echo "🚀 Starting Ollama service..."

        # Copy .env if not present
        if [ ! -f "$OLLAMA_DIR/.env" ]; then
            cp "$OLLAMA_DIR/.env.example" "$OLLAMA_DIR/.env" 2>/dev/null || true
        fi

        # ---- Image selection ----
        # OLLAMA_IMAGE can be set in environment:
        #   full:       OLLAMA_IMAGE=ollama/ollama:latest  (~4GB, CUDA)
        #   lightweight: OLLAMA_IMAGE=alpine/ollama:latest  (~70MB, CPU-only)
        OLLAMA_IMAGE="${OLLAMA_IMAGE:-ollama/ollama:latest}"
        echo "   Image: $OLLAMA_IMAGE"

        cd "$OLLAMA_DIR"
        OLLAMA_IMAGE="$OLLAMA_IMAGE" docker compose up --build -d
        cd "$ROOT_DIR"

        echo "✅ Ollama service starting in background"

        # ---- Wait for tinyllama to be ready ----
        echo "⏳ Waiting for tinyllama to be ready..."
        echo "   (First run pulls ~638MB — may take 2-3 minutes)"
        echo ""

        MAX_WAIT=240
        elapsed=0
        SPINNER="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spin_idx=0

        while [ "$elapsed" -lt "$MAX_WAIT" ]; do
            # Check if tinyllama is in the model list
            if curl -sf "${OLLAMA_ENDPOINT}/api/tags" 2>/dev/null \
               | grep -q "$OLLAMA_MODEL"; then
                echo ""
                echo "✅ $OLLAMA_MODEL ready! (${elapsed}s)"
                break
            fi

            # Spinner progress indicator
            spin_char="${SPINNER:$spin_idx:1}"
            printf "\r   %s Waiting... (%ds)" "$spin_char" "$elapsed"
            spin_idx=$(( (spin_idx + 1) % ${#SPINNER} ))

            sleep 5
            elapsed=$((elapsed + 5))
        done

        if [ "$elapsed" -ge "$MAX_WAIT" ]; then
            echo ""
            echo "⚠️  Ollama not ready after ${MAX_WAIT}s — continuing anyway"
            echo "   Check status: cd ollama-service && make status"
            echo "   Check logs:   cd ollama-service && docker compose logs ollama"
        fi

    else
        echo "⚠️  ollama-service not found at $OLLAMA_DIR"
        echo "   Ensure ollama-service/ folder exists in repo root"
    fi
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
echo "   Endpoint:  ${OLLAMA_ENDPOINT:-not set}"
echo "   Model:     ${OLLAMA_MODEL:-not set}"
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
echo "     make ollama        — local Ollama (default)"
echo "     make mock          — offline/plane mode"
echo "     make openai        — OpenAI API"
echo ""
