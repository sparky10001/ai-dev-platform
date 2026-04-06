###################################################################
# AI Dev Platform — Makefile
# Unified control surface for the AI development environment
#
# Core Principle: Only the AI interface is stable.
# Everything else can change, will change, should be replaceable.
###################################################################

.PHONY: setup openai colab local mock health ai-run ai-fix ai-explain ai-refactor switch help

# Default target
.DEFAULT_GOAL := help

###################################################################
# Setup & Installation
###################################################################

setup: ## Initialize environment from template
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env || true
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh
	@echo "✅ Setup complete — edit .env to configure your provider"
	@echo "   Then run: make openai | make colab | make local | make mock"

###################################################################
# Provider Switching
###################################################################

openai: ## Switch to OpenAI provider
	@echo "🔄 Switching to OpenAI..."
	@./scripts/switch-model.sh openai
	@echo "✅ Provider: OpenAI"
	@echo "   Ensure OPENAI_API_KEY is set in .env"

colab: ## Switch to Google Colab GPU proxy
	@echo "🔄 Starting Colab proxy..."
	@./scripts/start-colab-proxy.sh
	@./scripts/switch-model.sh colab
	@echo "✅ Provider: Colab GPU"

local: ## Switch to local model (private-ai-stack / Ollama)
	@echo "🔄 Switching to local model..."
	@./scripts/switch-model.sh local
	@echo "✅ Provider: Local"
	@echo "   Ensure MODEL_ENDPOINT is set in .env"

mock: ## Switch to mock adapter (offline/plane mode)
	@echo "🔄 Switching to mock adapter..."
	@./scripts/switch-model.sh mock
	@echo "✅ Provider: Mock (offline mode)"
	@echo "   No AI calls will be made"

###################################################################
# Health & Status
###################################################################

health: ## Check health of all services
	@./scripts/health-check.sh

status: ## Show current active provider and adapter
	@echo ""
	@echo "📊 AI Dev Platform Status"
	@echo "========================="
	@echo "Provider:  $$(grep MODEL_PROVIDER .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Adapter:   $$(grep AI_ADAPTER .env 2>/dev/null | cut -d= -f2 || echo 'not set')"
	@echo "Endpoint:  $$(grep MODEL_ENDPOINT .env 2>/dev/null | cut -d= -f2 || echo 'default')"
	@echo "Symlink:   $$(readlink scripts/adapters/ai.sh 2>/dev/null || echo 'not set')"
	@echo ""

###################################################################
# AI Commands — stable interface regardless of provider
###################################################################

ai-run: ## Run AI agent with command (CMD="your task here")
	@./scripts/adapters/ai.sh run "$(CMD)"

ai-fix: ## Ask AI to fix an issue (ISSUE="describe the problem")
	@./scripts/adapters/ai.sh fix "$(ISSUE)"

ai-explain: ## Ask AI to explain something (TOPIC="what to explain")
	@./scripts/adapters/ai.sh explain "$(TOPIC)"

ai-refactor: ## Ask AI to refactor code (TARGET="what to refactor")
	@./scripts/adapters/ai.sh refactor "$(TARGET)"

ai-query: ## Ask AI a general question (Q="your question")
	@./scripts/adapters/ai.sh query "$(Q)"

###################################################################
# Project Context Shortcuts
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
	@echo "🤖 AI Dev Platform — Available Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Examples:"
	@echo "    make setup                          # First time setup"
	@echo "    make openai                         # Switch to OpenAI"
	@echo "    make local                          # Switch to local Ollama"
	@echo "    make mock                           # Offline/plane mode"
	@echo "    make ai-run CMD='analyze agent-sim' # Run AI task"
	@echo "    make ai-fix ISSUE='broken import'   # Fix an issue"
	@echo "    make health                         # Check all services"
	@echo "    make status                         # Show current config"
	@echo ""
ai-dev-platform.Makefile
Displaying ai-dev-platform.Makefile.