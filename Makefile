###################################################################
# AI Dev Platform — Makefile (v6.5 production)
###################################################################

.PHONY: setup openai http colab local ollama mock mock-local \
        mock-server health status validate fallback-dev fallback-prod \
        ai-run ai-fix ai-explain ai-refactor ai-query help

.DEFAULT_GOAL := help

###################################################################
# Setup
###################################################################

setup:
	@echo "🔧 Setting up AI Dev Platform..."
	@cp -n .env.example .env 2>/dev/null || true
	@chmod +x ai
	@chmod +x tools/*.sh
	@chmod +x scripts/*.sh
	@chmod +x scripts/adapters/*.sh
	@chmod +x ollama-service/*.sh
	@echo "✅ Setup complete"

###################################################################
# Provider Switching
###################################################################

http:
	@./scripts/switch-model.sh http
	@echo "✅ Adapter: http-agent"

openai:
	@./scripts/switch-model.sh openai

ollama: ## NEW — native Ollama adapter
	@./scripts/switch-model.sh local
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=ollama --no-print-directory
	@echo "🏠 Using Ollama adapter (local LLM)"

local: ## OpenAI-compatible local endpoint
	@./scripts/switch-model.sh local
	@echo "⚠️ Using OpenAI-compatible local endpoint"

mock:
	@./scripts/switch-model.sh mock
	@echo "✅ Offline mode"

###################################################################
# 🔁 FALLBACK PROFILES (NEW)
###################################################################

fallback-dev: ## Offline-first chain
	@echo "🧪 Setting DEV fallback chain..."
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=mock,ollama,http-agent --no-print-directory
	@echo "✅ mock → ollama → http-agent"

fallback-prod: ## Production chain
	@echo "🚀 Setting PROD fallback chain..."
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,http-agent,openai --no-print-directory
	@echo "✅ ollama → http-agent → openai"

###################################################################
# Profiles (Upgraded)
###################################################################

profile-fast:
	@echo "⚡ FAST (no fallback)"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=openai
	@$(MAKE) _set-env KEY=FALLBACK_ENABLED VALUE=false
	@$(MAKE) profile

profile-agent:
	@echo "🦆 AGENT (goose + fallback)"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=goose
	@$(MAKE) _set-env KEY=FALLBACK_ENABLED VALUE=true
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,http-agent
	@$(MAKE) profile

profile-offline:
	@echo "🛑 OFFLINE"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=mock
	@$(MAKE) _set-env KEY=FALLBACK_ENABLED VALUE=false
	@$(MAKE) profile

profile-local:
	@echo "🏠 LOCAL HYBRID"
	@$(MAKE) _set-env KEY=AI_ADAPTER VALUE=ollama
	@$(MAKE) _set-env KEY=FALLBACK_CHAIN VALUE=ollama,http-agent
	@$(MAKE) _set-env KEY=FALLBACK_ENABLED VALUE=true
	@$(MAKE) profile

profile:
	@echo ""
	@echo "🎯 Active Profile"
	@echo "=================="
	@echo "Adapter:   $$(grep '^AI_ADAPTER=' .env | cut -d= -f2)"
	@echo "Provider:  $$(grep '^MODEL_PROVIDER=' .env | cut -d= -f2)"
	@echo "Endpoint:  $$(grep '^MODEL_ENDPOINT=' .env | cut -d= -f2)"
	@echo "Fallback:  $$(grep '^FALLBACK_CHAIN=' .env | cut -d= -f2)"
	@echo ""

###################################################################
# Status (Enhanced)
###################################################################

status:
	@echo ""
	@echo "📊 AI Dev Platform Status"
	@echo "========================="
	@echo "Provider:   $$(grep '^MODEL_PROVIDER=' .env | cut -d= -f2)"
	@echo "Adapter:    $$(grep '^AI_ADAPTER=' .env | cut -d= -f2)"
	@echo "Endpoint:   $$(grep '^MODEL_ENDPOINT=' .env | cut -d= -f2)"
	@echo "Fallback:   $$(grep '^FALLBACK_CHAIN=' .env | cut -d= -f2)"
	@echo "FallbackOn: $$(grep '^FALLBACK_ENABLED=' .env | cut -d= -f2)"
	@echo ""

###################################################################
# Validation (Upgraded)
###################################################################

validate:
	@echo "🪜 Running validation ladder..."

	@echo "1️⃣ Mock (offline)"
	@make mock --no-print-directory
	@./scripts/runtime.sh run "test"

	@echo "2️⃣ Ollama (if running)"
	@make ollama --no-print-directory || true
	@./scripts/runtime.sh run "test" || true

	@echo "3️⃣ HTTP adapter"
	@make http --no-print-directory
	@./scripts/runtime.sh run "test"

	@echo "4️⃣ Fallback chain"
	@$(MAKE) fallback-dev --no-print-directory
	@./scripts/runtime.sh run "force failure test"

	@echo "✅ Validation complete"

###################################################################
# AI Commands (unchanged)
###################################################################

ai-run:
	@./scripts/runtime.sh run "$(CMD)"

ai-fix:
	@./scripts/runtime.sh fix "$(ISSUE)"

ai-explain:
	@./scripts/runtime.sh explain "$(TOPIC)"

ai-refactor:
	@./scripts/runtime.sh refactor "$(TARGET)"

ai-query:
	@./scripts/runtime.sh query "$(Q)"

###################################################################
# Internal
###################################################################

_set-env:
	@grep -q "^$(KEY)=" .env && \
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
	@echo "Providers:"
	@echo "  make openai | http | ollama | mock"
	@echo ""
	@echo "Fallback:"
	@echo "  make fallback-dev"
	@echo "  make fallback-prod"
	@echo ""
	@echo "Profiles:"
	@echo "  make profile-fast | profile-agent | profile-local"
	@echo ""
	@echo "Run:"
	@echo "  make ai-run CMD='your task'"
	@echo ""