###################################################################
# AI Dev Platform — Makefile
# Unified control surface for the AI development environment
#
# Core Principle: Only the AI interface is stable.
# Everything else can change, will change, should be replaceable.
###################################################################

.PHONY: setup openai colab local mock mock-local mock-server \
        health status ai-run ai-fix ai-explain ai-refactor ai-query \
        ctx-agent-sim ctx-arb ctx-ai-stack help

.DEFAULT_GOAL := help

###################################################################
# Setup & Installation
###################################################################

setup: ## Initialize environment from template
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env 2>/dev/null || true
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh
	@pip install -r scripts/mock-server/requirements.txt -q 2>/dev/null || true
	@echo "✅ Setup complete — edit .env to configure your provider"
	@echo "   Then run: make openai | make local | make mock"

###################################################################
# Provider Switching
###################################################################

openai: ## Switch to OpenAI provider
	@./scripts/switch-model.sh openai

colab: ## Switch to Google Colab GPU proxy
	@./scripts/start-colab-proxy.sh
	@./scripts/switch-model.sh colab

local: ## Switch to local model (private-ai-stack / Ollama)
	@./scripts/switch-model.sh local

mock: ## Switch to mock adapter (offline — no API calls)
	@./scripts/switch-model.sh mock
	@echo "✅ Offline mode — no AI calls will be made"

mock-local: ## Switch Goose to local mock OpenAI server
	@./scripts/switch-model.sh mock-local
	@echo "   Run 'make mock-server' in another terminal first!"

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
		echo "❌ Mock server failed to start — check /tmp/mock-server.log"

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
	@echo "1️⃣  Health check:"
	@curl -sf http://localhost:8000/health | python3 -m json.tool || \
		echo "❌ Server not running — start with: make mock-server-bg"
	@echo ""
	@echo "2️⃣  Models:"
	@curl -sf http://localhost:8000/v1/models | python3 -m json.tool
	@echo ""
	@echo "3️⃣  Chat completion:"
	@curl -sf http://localhost:8000/v1/chat/completions \
		-H "Content-Type: application/json" \
		-d '{"model":"mock-model","messages":[{"role":"user","content":"hello from make test"}]}' \
		| python3 -m json.tool

###################################################################
# Health & Status
###################################################################

health: ## Check health of all platform components
	@./scripts/health-check.sh

status: ## Show current active provider and adapter
	@echo ""
	@echo "📊 AI Dev Platform Status"
	@echo "========================="
	@echo "Provider:  $$(grep '^MODEL_PROVIDER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Adapter:   $$(grep '^AI_ADAPTER=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Endpoint:  $$(grep '^MODEL_ENDPOINT=' .env 2>/dev/null | cut -d= -f2 || echo 'default')"
	@echo "Symlink:   $$(readlink scripts/adapters/ai.sh 2>/dev/null || echo 'not set')"
	@echo "Project:   $$(grep '^ACTIVE_PROJECT=' .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo ""

###################################################################
# Validation Ladder
###################################################################

validate: ## Run full validation ladder (mock → mock-local → status)
	@echo "🪜 Running validation ladder..."
	@echo ""
	@echo "Step 1️⃣  — Mock adapter (no network)"
	@make mock --no-print-directory
	@./scripts/adapters/ai.sh run "validation test step 1"
	@echo ""
	@echo "Step 2️⃣  — Mock server (local API)"
	@make mock-server-bg --no-print-directory
	@sleep 2
	@make mock-local --no-print-directory
	@./scripts/adapters/ai.sh run "validation test step 2"
	@make mock-server-stop --no-print-directory
	@echo ""
	@echo "✅ Validation ladder complete!"
	@echo "   Next: make local | make openai | make colab"

###################################################################
# AI Commands — stable interface
###################################################################

ai-run: ## Run AI agent with command  (CMD="your task here")
	@./scripts/ai run "$(CMD)"

ai-fix: ## Ask AI to fix an issue    (ISSUE="describe the problem")
	@./scripts/ai fix "$(ISSUE)"

ai-explain: ## Ask AI to explain      (TOPIC="what to explain")
	@./scripts/ai explain "$(TOPIC)"

ai-refactor: ## Ask AI to refactor    (TARGET="what to refactor")
	@./scripts/ai refactor "$(TARGET)"

ai-query: ## Ask AI a question        (Q="your question")
	@./scripts/ai query "$(Q)"

###################################################################
# Project Context
###################################################################

ctx-agent-sim: ## Set active project context to agent-sim
	@sed -i 's/^ACTIVE_PROJECT=.*/ACTIVE_PROJECT=agent-sim/' .env
	@echo "✅ Context: agent-sim"

ctx-arb: ## Set active project context to arb-agent-system
	@sed -i 's/^ACTIVE_PROJECT=.*/ACTIVE_PROJECT=arb-agent-system/' .env
	@echo "✅ Context: arb-agent-system"

ctx-ai-stack: ## Set active project context to private-ai-stack
	@sed -i 's/^ACTIVE_PROJECT=.*/ACTIVE_PROJECT=private-ai-stack/' .env
	@echo "✅ Context: private-ai-stack"

###################################################################
# Help
###################################################################

help: ## Show this help message
	@echo ""
	@echo "🤖 AI Dev Platform — Commands"
	@echo "=============================="
	@echo ""
	@echo "  PROVIDERS:"
	@grep -E '^(openai|colab|local|mock|mock-local):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  MOCK SERVER:"
	@grep -E '^mock-server.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  HEALTH:"
	@grep -E '^(health|status|validate):.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  AI COMMANDS:"
	@grep -E '^ai-.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  CONTEXT:"
	@grep -E '^ctx-.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Examples:"
	@echo "    make mock-server-bg              # Start mock in background"
	@echo "    make mock-local                  # Point Goose at mock"
	@echo "    make mock-server-test            # Validate mock endpoints"
	@echo "    make ai-run CMD='hello world'    # Run AI task"
	@echo "    make validate                    # Full validation ladder"
	@echo ""
