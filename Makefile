###################################################################
# AI Dev Platform — Makefile (v7.0 production)
#
# Fixes from v6.5:
# - Restored goose / openai-goose provider target
# - Fixed profile-agent to properly configure Goose
# - All ai-* commands use ./ai (stable interface) not runtime.sh
# - Validate uses ./ai not runtime.sh
# - Restored mock-server targets
# - Restored mock-local target
# - Restored colab target
# - Restored ctx-* context switching targets
# - Fixed setup chmod paths
# - Fixed health target (was empty)
###################################################################

.PHONY: setup install-goose \
        openai openai-goose http colab ollama local mock mock-local \
        mock-server mock-server-bg mock-server-stop mock-server-test \
        fallback-dev fallback-prod \
        profile-fast profile-agent profile-offline profile-local profile \
        health status validate \
        ai-run ai-fix ai-explain ai-refactor ai-query \
        ctx-agent-sim ctx-arb ctx-ai-stack \
        help _set-env

.DEFAULT_GOAL := help

###################################################################
# Setup & Installation
###################################################################

setup: ## Initialize environment from template
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env 2>/dev/null || true
	@chmod +x ai
	@chmod +x ai-eval 2>/dev/null || true
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh
	@chmod +x scripts/tool_executor.sh 2>/dev/null || true
	@chmod +x ollama-service/entrypoint.sh 2>/dev/null || true
	@pip install -r scripts/mock-server/requirements.txt -q 2>/dev/null || true
	@echo "✅ Setup complete — edit .env to configure your provider"
	@echo "   Then run: make ollama | make mock | make openai"

install-goose: ## Install Goose CLI (official installer, user-local)
	@echo "🦆 Installing Goose CLI (official script)..."
	@set -e; \
	if command -v goose >/dev/null 2>&1; then \
	  echo "✅ Goose already installed: $$(which goose)"; \
	  exit 0; \
	fi; \
	echo "⬇️  Running official installer..."; \
	curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \
	  | CONFIGURE=false bash; \
	if command -v goose >/dev/null 2>&1; then \
	  echo "✅ Goose installed: $$(which goose)"; \
	else \
	  echo "❌ Goose install failed (binary not found in PATH)"; \
	  echo "👉 Try: export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
	  exit 1; \
	fi

###################################################################
# Provider Switching
###################################################################

openai: ## Switch to OpenAI API
	@./scripts/switch-model.sh openai

openai-goose: ## Switch to OpenAI via Goose agent
	@./scripts/switch-model.sh openai-goose
	@echo "🦆 Using Goose as agent with OpenAI backend"

http: ## Switch to generic HTTP adapter (mock server / local endpoint)
	@./scripts/switch-model.sh http

colab: ## Switch to Google Colab GPU proxy
	@./scripts/start-colab-proxy.sh
	@./scripts/switch-model.sh colab

ollama: ## Switch to local Ollama LLM (native adapter)
	@./scripts/switch-model.sh ollama

local: ## Switch to OpenAI-compatible local endpoint
	@./scripts/switch-model.sh local

mock: ## Switch to mock adapter (offline — no AI calls)
	@./scripts/switch-model.sh mock

mock-local: ## Switch to local mock OpenAI server
	@./scripts/switch-model.sh mock-local
	@echo "   Start server first: make mock-server-bg"

###################################################################
# Mock Server
###################################################################

mock-server: ## Start local OpenAI-compatible mock server (port 8000)
	@echo "🧪 Starting mock OpenAI server on port 8000..."
	@echo "   Press Ctrl+C to stop"
	@echo ""
	cd scripts/mock-server && uvicorn mock_openai:app \
		--host 0.0.0.0 \
		--port 8000 \
		--reload

mock-server-bg: ## Start mock server in background
	@echo "🧪 Starting mock server in background..."
	@cd scripts/mock-server && \
		uvicorn mock_openai:app --host 0.0.0.0 --port 8000 \
		> /tmp/mock-server.log 2>&1 & \
		echo $$! > /tmp/mock-server.pid
	@sleep 2
	@curl -sf http://localhost:8000/health > /dev/null && \
		echo "✅ Mock server running (PID: $$(cat /tmp/mock-server.pid))" || \
		echo "❌ Mock server failed — check /tmp/mock-server.log"

mock-server-stop: ## Stop background mock server
	@if [ -f /tmp/mock-server.pid ]; then \
		kill $$(cat /tmp/mock-server.pid) 2>/dev/null && \
		rm /tmp/mock-server.pid && \
		echo "✅ Mock server stopped"; \
	else \
		echo "⚠️  No mock server PID found"; \
	fi

mock-server-test: ## Test mock server endpoints
	@echo "🧪 Testing mock server..."
	@echo ""
	@echo "1️⃣  Health:"
	@curl -sf http://localhost:8000/health | python3 -m json.tool || \
		echo "❌ Not running — start with: make mock-server-bg"
	@echo ""
	@echo "2️⃣  Models:"
	@curl -sf http://localhost:8000/v1/models | python3 -m json.tool
	@echo ""
	@echo "3️⃣  Chat completion:"
	@curl -sf http://localhost:8000/v1/chat/completions \
		-H "Content-Type: application/json" \
		-d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}]}' \
		| python3 -m json.tool

###################################################################
# Fallback Profiles
###################################################################

fallback-dev: ## Offline-first fallback chain (dev/plane use)
	@echo "🧪 Setting DEV fallback chain..."
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,mock --no-print-directory
	@echo "✅ ollama → mock"

fallback-prod: ## Production fallback chain
	@echo "🚀 Setting PROD fallback chain..."
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,http-agent,openai --no-print-directory
	@echo "✅ ollama → http-agent → openai"

###################################################################
# Profiles
###################################################################

profile-fast: ## Fast — OpenAI direct, no fallback
	@echo "⚡ FAST profile"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=openai --no-print-directory
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=mock --no-print-directory
	@$(MAKE) profile --no-print-directory

profile-agent: ## Agent — Goose with Ollama fallback
	@echo "🦆 AGENT profile"
	@./scripts/switch-model.sh openai-goose
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,http-agent,mock --no-print-directory
	@$(MAKE) profile --no-print-directory

profile-offline: ## Offline — mock only, no network
	@echo "🛑 OFFLINE profile"
	@./scripts/switch-model.sh mock
	@$(MAKE) profile --no-print-directory

profile-local: ## Local hybrid — Ollama with mock fallback
	@echo "🏠 LOCAL profile"
	@./scripts/switch-model.sh ollama
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,mock --no-print-directory
	@$(MAKE) profile --no-print-directory

profile: ## Show active profile
	@echo ""
	@echo "🎯 Active Profile"
	@echo "=================="
	@echo "Adapter:   $$(grep '^AI_ADAPTER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Provider:  $$(grep '^MODEL_PROVIDER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Endpoint:  $$(grep '^MODEL_ENDPOINT=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Fallback:  $$(grep '^FALLBACK_CHAIN=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo ""

###################################################################
# Health & Status
###################################################################

health: ## Check health of all platform components
	@./scripts/health-check.sh

status: ## Show current active provider and adapter
	@echo ""
	@echo "📊 AI Dev Platform Status"
	@echo "========================="
	@echo "Provider:   $$(grep '^MODEL_PROVIDER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Adapter:    $$(grep '^AI_ADAPTER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Endpoint:   $$(grep '^MODEL_ENDPOINT=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Fallback:   $$(grep '^FALLBACK_CHAIN=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Ollama:     $$(grep '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Project:    $$(grep '^ACTIVE_PROJECT=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo ""

###################################################################
# Validation Ladder
# Uses ./ai (stable interface) — not runtime.sh directly
###################################################################

validate: ## Run full validation ladder
	@echo "🪜 Running validation ladder..."
	@echo ""
	@echo "Step 1️⃣  — Mock adapter (no network)"
	@make mock --no-print-directory
	@./ai run "validation test step 1"
	@echo ""
	@echo "Step 2️⃣  — Mock server (local API)"
	@make mock-server-bg --no-print-directory
	@sleep 2
	@make mock-local --no-print-directory
	@./ai run "validation test step 2"
	@make mock-server-stop --no-print-directory
	@echo ""
	@echo "Step 3️⃣  — Ollama (local LLM)"
	@make ollama --no-print-directory
	@./ai run "say hello in one word" || echo "⚠️  Ollama not available — skipping"
	@echo ""
	@echo "✅ Validation complete!"
	@echo "   Next: make openai | make colab"

###################################################################
# AI Commands
# All use ./ai (stable interface) — never runtime.sh directly
###################################################################

ai-run: ## Run AI agent with command  (CMD="your task here")
	@./ai run "$(CMD)"

ai-fix: ## Ask AI to fix an issue    (ISSUE="describe the problem")
	@./ai fix "$(ISSUE)"

ai-explain: ## Ask AI to explain      (TOPIC="what to explain")
	@./ai explain "$(TOPIC)"

ai-refactor: ## Ask AI to refactor    (TARGET="what to refactor")
	@./ai refactor "$(TARGET)"

ai-query: ## Ask AI a question        (Q="your question")
	@./ai query "$(Q)"

###################################################################
# Project Context
###################################################################

ctx-agent-sim: ## Set active project context to agent-sim
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=agent-sim --no-print-directory
	@echo "✅ Context: agent-sim"

ctx-arb: ## Set active project context to arb-agent-system
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=arb-agent-system --no-print-directory
	@echo "✅ Context: arb-agent-system"

ctx-ai-stack: ## Set active project context to private-ai-stack
	@$(MAKE) _set-env KEY=ACTIVE_PROJECT VALUE=private-ai-stack --no-print-directory
	@echo "✅ Context: private-ai-stack"

###################################################################
# Internal helpers
###################################################################

_set-env: ## Internal: set a key=value in .env
	@grep -q "^$(KEY)=" .env 2>/dev/null && \
		sed -i "s|^$(KEY)=.*|$(KEY)=$(VALUE)|" .env || \
		echo "$(KEY)=$(VALUE)" >> .env

###################################################################
# Help
###################################################################

help: ## Show this help message
	@echo ""
	@echo "🤖 AI Dev Platform — Commands"
	@echo "=============================="
	@echo ""
	@echo "  SETUP:"
	@grep -E '^(setup|install-goose):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  PROVIDERS:"
	@grep -E '^(openai|openai-goose|http|colab|ollama|local|mock|mock-local):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  MOCK SERVER:"
	@grep -E '^mock-server.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  FALLBACK:"
	@grep -E '^fallback-.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  PROFILES:"
	@grep -E '^profile.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  HEALTH:"
	@grep -E '^(health|status|validate):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  AI COMMANDS:"
	@grep -E '^ai-.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  CONTEXT:"
	@grep -E '^ctx-.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Examples:"
	@echo "    make ollama                       # Switch to local Ollama"
	@echo "    make openai-goose                 # Use Goose with OpenAI"
	@echo "    make profile-local                # Local hybrid profile"
	@echo "    make ai-run CMD='hello world'     # Run AI task"
	@echo "    make ctx-agent-sim                # Switch project context"
	@echo "    make validate                     # Full validation ladder"
	@echo ""
