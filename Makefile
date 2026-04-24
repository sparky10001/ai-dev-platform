###################################################################
# AI Dev Platform — Makefile (v8.0 LiteLLM-native)
#
# Key Changes:
# - LiteLLM is the primary provider
# - Goose is a runtime (adapter), not a provider
# - Removed legacy OpenAI/Ollama/http-agent targets
# - Improved validation ladder (clear success/failure)
# - Added LiteLLM model profiles (fast/code/claude)
# - Cleaned help output
###################################################################

.PHONY: setup install-goose \
        litellm goose colab local mock mock-local \
        mock-server mock-server-bg mock-server-stop mock-server-test \
        fallback-dev fallback-prod \
        profile-fast profile-agent profile-offline profile-local profile \
        litellm-fast litellm-code litellm-claude \
        health status validate \
        ai-run ai-fix ai-explain ai-refactor ai-query \
        ctx-agent-sim ctx-arb ctx-ai-stack \
        help _set-env

.DEFAULT_GOAL := help

###################################################################
# Setup & Installation
###################################################################

setup:
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env 2>/dev/null || true
	@chmod +x ai
	@chmod +x ai-eval 2>/dev/null || true
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh
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
# Provider / Runtime Switching
###################################################################

litellm:
	@./scripts/switch-model.sh litellm

goose:
	@./scripts/switch-model.sh goose
	@echo "🦆 Goose runtime enabled (via LiteLLM)"

colab:
	@./scripts/start-colab-proxy.sh
	@./scripts/switch-model.sh colab

local:
	@./scripts/switch-model.sh local

mock:
	@./scripts/switch-model.sh mock

mock-local:
	@./scripts/switch-model.sh mock-local
	@echo "   Start server first: make mock-server-bg"

###################################################################
# Mock Server
###################################################################

mock-server:
	@echo "🧪 Starting mock server..."
	cd scripts/mock-server && uvicorn mock_openai:app --host 0.0.0.0 --port 8000 --reload

mock-server-bg:
	@echo "🧪 Starting mock server (background)..."
	@cd scripts/mock-server && \
		uvicorn mock_openai:app --host 0.0.0.0 --port 8000 \
		> /tmp/mock-server.log 2>&1 & \
		echo $$! > /tmp/mock-server.pid
	@sleep 2
	@curl -sf http://localhost:8000/health > /dev/null && \
		echo "✅ Mock server running" || \
		(echo "❌ Mock server failed"; exit 1)

mock-server-stop:
	@if [ -f /tmp/mock-server.pid ]; then \
		kill $$(cat /tmp/mock-server.pid) 2>/dev/null && \
		rm /tmp/mock-server.pid && \
		echo "✅ Mock server stopped"; \
	else \
		echo "⚠️  No mock server PID found"; \
	fi

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
# Profiles
###################################################################

profile-fast:
	@echo "⚡ FAST"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=litellm --no-print-directory
	@$(MAKE) _set-env KEY=ACTIVE_MODEL VALUE=fast --no-print-directory

profile-agent:
	@echo "🦆 AGENT"
	@./scripts/switch-model.sh goose

profile-offline:
	@echo "🛑 OFFLINE"
	@./scripts/switch-model.sh mock

profile-local:
	@echo "🏠 LOCAL"
	@./scripts/switch-model.sh litellm
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=litellm,mock --no-print-directory

profile:
	@echo ""
	@echo "🎯 Active Profile"
	@echo "=================="
	@grep -E 'MODEL_PROVIDER|AI_ADAPTER|MODEL_ENDPOINT|FALLBACK_CHAIN|ACTIVE_MODEL' .env || true
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
	@grep -E 'MODEL_PROVIDER|AI_ADAPTER|MODEL_ENDPOINT|FALLBACK_CHAIN|ACTIVE_MODEL' .env || true
	@echo ""

###################################################################
# Validation Ladder (HARDENED)
###################################################################

validate:
	@echo "🪜 Validation ladder"
	@echo ""

	@echo "Step 1 — Mock"
	@make mock --no-print-directory
	@./ai run "ping" | grep -q "mock" && echo "✅ Mock OK" || (echo "❌ Mock failed"; exit 1)

	@echo ""
	@echo "Step 2 — Mock server"
	@make mock-server-bg --no-print-directory
	@make mock-local --no-print-directory
	@./ai run "ping" && echo "✅ Mock API OK" || (echo "❌ Mock API failed"; exit 1)
	@make mock-server-stop --no-print-directory

	@echo ""
	@echo "Step 3 — LiteLLM"
	@make litellm --no-print-directory
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
# Context
###################################################################

ctx-agent-sim:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=agent-sim --no-print-directory

ctx-arb:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=arb-agent-system --no-print-directory

ctx-ai-stack:
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=private-ai-stack --no-print-directory

###################################################################
# Internal
###################################################################

_set-env:
	@grep -q "^$(KEY)=" .env 2>/dev/null && \
		sed -i "s|^$(KEY)=.*|$(KEY)=$(VALUE)|" .env || \
		echo "$(KEY)=$(VALUE)" >> .env

###################################################################
# Help
###################################################################

help:
	@echo ""
	@echo "🤖 AI Dev Platform"
	@echo "=================="
	@echo ""
	@echo "Core:"
	@echo "  make litellm          # Use LiteLLM"
	@echo "  make goose            # Use Goose agent"
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