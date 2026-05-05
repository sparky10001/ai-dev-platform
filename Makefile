###################################################################
# AI Dev Platform — Makefile (v9.0 LiteLLM-first, switch-model aligned)
#
# Key Improvements:
# - Fully aligned with switch-model.sh v6.0
# - LiteLLM is the single gateway
# - Goose = runtime adapter only
# - Removed invalid/legacy providers (local/http-agent/etc.)
# - Hardened validation + mock lifecycle
# - Backwards-compatible env handling
###################################################################

.PHONY: setup install-goose \
        litellm goose colab mock mock-local \
        mock-server mock-server-bg mock-server-stop \
        fallback-dev fallback-prod \
        profile-fast profile-agent profile-offline profile-local profile \
        litellm-fast litellm-code litellm-claude \
        health status validate \
        ai-run ai-fix ai-explain ai-refactor ai-query \
        ctx-agent-sim ctx-arb ctx-ai-stack \
        help _set-env

.DEFAULT_GOAL := help

ENV_FILE := .env

###################################################################
# Setup & Installation
###################################################################

setup:
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env 2>/dev/null || true
	@chmod +x ai 2>/dev/null || true
	@chmod +x ai-eval 2>/dev/null || true
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh 2>/dev/null || true
	@chmod +x scripts/tool_executor.sh 2>/dev/null || true
	@pip install -r scripts/mock-server/requirements.txt -q 2>/dev/null || true
	@echo "✅ Setup complete"

install-goose:
	@echo "🦆 Installing Goose CLI..."
	@set -e; \
	if command -v goose >/dev/null 2>&1; then \
	  echo "✅ Goose already installed"; exit 0; \
	fi; \
	curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \
	  | CONFIGURE=false bash

###################################################################
# Provider / Runtime Switching (delegates to switch-model.sh)
###################################################################

litellm:
	@./scripts/switch-model.sh litellm

goose:
	@./scripts/switch-model.sh goose
	@echo "🦆 Goose runtime enabled (via LiteLLM)"

colab:
	@./scripts/start-colab-proxy.sh
	@./scripts/switch-model.sh colab

mock:
	@./scripts/switch-model.sh mock

mock-local:
	@./scripts/switch-model.sh mock-local
	@echo "   Start server first: make mock-server-bg"

###################################################################
# Mock Server (HARDENED)
###################################################################

MOCK_PORT ?= 8000
MOCK_PID_FILE := /tmp/mock-server.pid
MOCK_LOG_FILE := /tmp/mock-server.log

# ---------------------------------------------------------------
# Check if port is in use
# ---------------------------------------------------------------
_port_in_use:
	@lsof -i :$(MOCK_PORT) >/dev/null 2>&1 && echo "IN_USE" || true

# ---------------------------------------------------------------
# Stop server (safe)
# ---------------------------------------------------------------
mock-server-stop:
	@echo "🛑 Stopping mock server..."
	@if [ -f $(MOCK_PID_FILE) ]; then \
		PID=$$(cat $(MOCK_PID_FILE)); \
		if kill -0 $$PID >/dev/null 2>&1; then \
			kill $$PID && echo "✅ Stopped PID $$PID"; \
		else \
			echo "⚠️  Stale PID file (process not running)"; \
		fi; \
		rm -f $(MOCK_PID_FILE); \
	else \
		echo "⚠️  No PID file"; \
	fi

	@# Fallback: kill anything on port
	@lsof -ti :$(MOCK_PORT) | xargs -r kill -9 2>/dev/null || true

# ---------------------------------------------------------------
# Start (foreground)
# ---------------------------------------------------------------
mock-server:
	@$(MAKE) mock-server-stop --no-print-directory
	@echo "🧪 Starting mock server..."
	cd scripts/mock-server && \
	uvicorn mock_openai:app --host 0.0.0.0 --port $(MOCK_PORT) --reload

# ---------------------------------------------------------------
# Start (background, hardened)
# ---------------------------------------------------------------
mock-server-bg:
	@$(MAKE) mock-server-stop --no-print-directory
	@echo "🧪 Starting mock server (background)..."

	@cd scripts/mock-server && \
		uvicorn mock_openai:app --host 0.0.0.0 --port $(MOCK_PORT) \
		> $(MOCK_LOG_FILE) 2>&1 & \
		echo $$! > $(MOCK_PID_FILE)

	@echo "⏳ Waiting for server..."

	@bash -c '\
	for i in 1 2 3 4 5; do \
		if curl -sf http://localhost:$(MOCK_PORT)/health >/dev/null; then \
			echo "✅ Mock server running"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "❌ Mock server failed"; \
	echo "---- LOG ----"; \
	cat $(MOCK_LOG_FILE); \
	exit 1; \
	'

# ---------------------------------------------------------------
# Test endpoint
# ---------------------------------------------------------------
mock-server-test:
	@curl -s http://localhost:$(MOCK_PORT)/health | jq .

###################################################################
# Fallback Profiles
###################################################################

fallback-dev:
	@echo "🧪 DEV fallback"
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=litellm,mock --no-print-directory

fallback-prod:
	@echo "🚀 PROD fallback"
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=litellm,goose,mock --no-print-directory

###################################################################
# Profiles (aligned with LiteLLM model abstraction)
###################################################################

profile-fast:
	@echo "⚡ FAST profile"
	@$(MAKE) _set-env KEY=ACTIVE_MODEL VALUE=fast --no-print-directory
	@$(MAKE) litellm --no-print-directory

profile-agent:
	@echo "🦆 AGENT profile"
	@$(MAKE) goose --no-print-directory

profile-offline:
	@echo "🛑 OFFLINE profile"
	@$(MAKE) mock --no-print-directory

profile-local:
	@echo "🏠 LOCAL dev profile"
	@$(MAKE) litellm --no-print-directory
	@$(MAKE) fallback-dev --no-print-directory

profile:
	@echo ""
	@echo "🎯 Active Profile"
	@echo "=================="
	@grep -E 'MODEL_PROVIDER|AI_ADAPTER|MODEL_ENDPOINT|FALLBACK_CHAIN|ACTIVE_MODEL' $(ENV_FILE) || true
	@echo ""

###################################################################
# LiteLLM Model Profiles
###################################################################

litellm-fast:
	@echo "⚡ LiteLLM FAST"
	@$(MAKE) _set-env KEY=ACTIVE_MODEL VALUE=fast --no-print-directory
	@$(MAKE) litellm --no-print-directory

litellm-code:
	@echo "🧠 LiteLLM CODE"
	@$(MAKE) _set-env KEY=ACTIVE_MODEL VALUE=code --no-print-directory
	@$(MAKE) litellm --no-print-directory

litellm-claude:
	@echo "🧠 LiteLLM CLAUDE"
	@$(MAKE) _set-env KEY=ACTIVE_MODEL VALUE=claude --no-print-directory
	@$(MAKE) litellm --no-print-directory

###################################################################
# Health & Status
###################################################################

health:
	@./scripts/health-check.sh

status:
	@echo ""
	@echo "📊 Status"
	@echo "=========="
	@grep -E 'MODEL_PROVIDER|AI_ADAPTER|MODEL_ENDPOINT|FALLBACK_CHAIN|ACTIVE_MODEL' $(ENV_FILE) || true
	@echo ""

###################################################################
# Validation Ladder (HARDENED)
###################################################################

validate:
	@echo "🪜 Validation ladder"
	@echo ""

	@echo "Step 1 — Mock (offline)"
	@$(MAKE) mock --no-print-directory
	@./ai run "ping" | grep -q "mock" && echo "✅ Mock OK" || (echo "❌ Mock failed"; exit 1)

	@echo ""
	@echo "Step 2 — Mock server (OpenAI-compatible)"
	@$(MAKE) mock-server-bg --no-print-directory
	@$(MAKE) mock-local --no-print-directory
	@./ai run "ping" && echo "✅ Mock API OK" || (echo "❌ Mock API failed"; exit 1)
	@$(MAKE) mock-server-stop --no-print-directory

	@echo ""
	@echo "Step 3 — LiteLLM"
	@$(MAKE) litellm --no-print-directory
	@./ai run "hello" && echo "✅ LiteLLM OK" || echo "⚠️ LiteLLM unavailable"

	@echo ""
	@echo "🎉 Validation complete"

###################################################################
# AI Commands
###################################################################

ai-run:
	@./ai run "$(CMD)"

ai-fix:
	@./ai fix "$(ISSUE)"

ai-explain:
	@./ai explain "$(TOPIC)"

ai-refactor:
	@./ai refactor "$(TARGET)"

ai-query:
	@./ai query "$(Q)"

###################################################################
# Context Switching
###################################################################

ctx-agent-sim:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=agent-sim --no-print-directory

ctx-arb:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=arb-agent-system --no-print-directory

ctx-ai-stack:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=private-ai-stack --no-print-directory

###################################################################
# Internal Helpers
###################################################################

_set-env:
	@grep -q "^$(KEY)=" $(ENV_FILE) 2>/dev/null && \
		sed -i "s|^$(KEY)=.*|$(KEY)=$(VALUE)|" $(ENV_FILE) || \
		echo "$(KEY)=$(VALUE)" >> $(ENV_FILE)

###################################################################
# Help
###################################################################

help:
	@echo ""
	@echo "🤖 AI Dev Platform"
	@echo "=================="
	@echo ""
	@echo "Core:"
	@echo "  make litellm          # Use LiteLLM gateway"
	@echo "  make goose            # Goose agent runtime"
	@echo "  make mock             # Offline mode"
	@echo ""
	@echo "Models:"
	@echo "  make litellm-fast"
	@echo "  make litellm-code"
	@echo "  make litellm-claude"
	@echo ""
	@echo "Dev:"
	@echo "  make validate"
	@echo "  make status"
	@echo ""