###################################################################
# LiteLLM Service — Makefile
###################################################################

.PHONY: up down build logs shell test status clean help
.DEFAULT_GOAL := help

up: ## Build and start LiteLLM service
	@echo "🔀 Starting LiteLLM service..."
	@docker compose up --build -d
	@sleep 3
	@make status --no-print-directory

down: ## Stop LiteLLM service
	@docker compose down
	@echo "✅ LiteLLM service stopped"

build: ## Build image only
	@docker compose build

logs: ## Follow service logs
	@docker compose logs -f litellm

shell: ## Open shell in running container
	@docker exec -it litellm /bin/bash || docker exec -it litellm /bin/sh

test: ## Run validation tests
	@echo "🧪 Running LiteLLM validation tests..."
	@docker compose --profile test up --abort-on-container-exit litellm-test

status: ## Show service status
	@echo ""
	@echo "📊 LiteLLM Service Status"
	@echo "========================="
	@docker compose ps
	@echo ""
	@echo "🔍 Health check:"
	@curl -sf http://localhost:4000/health 2>/dev/null \
		| python3 -m json.tool 2>/dev/null \
		|| echo "   ❌ Not reachable"
	@echo ""

model-fast: ## Switch active model to fast (tinyllama)
	@sed -i 's/^ACTIVE_MODEL=.*/ACTIVE_MODEL=fast/' .env
	@docker compose restart litellm
	@echo "✅ Active model: fast (tinyllama)"

model-code: ## Switch active model to code (gpt-4.1 → tinyllama fallback)
	@sed -i 's/^ACTIVE_MODEL=.*/ACTIVE_MODEL=code/' .env
	@docker compose restart litellm
	@echo "✅ Active model: code (gpt-4.1)"

model-claude: ## Switch active model to claude (claude-sonnet → tinyllama fallback)
	@sed -i 's/^ACTIVE_MODEL=.*/ACTIVE_MODEL=claude/' .env
	@docker compose restart litellm
	@echo "✅ Active model: claude (claude-sonnet)"

model-smart: ## Switch active model to smart (best available)
	@sed -i 's/^ACTIVE_MODEL=.*/ACTIVE_MODEL=smart/' .env
	@docker compose restart litellm
	@echo "✅ Active model: smart (best available)"

chat: ## Quick chat test (MODEL=fast MSG="hello")
	@curl -sf http://localhost:4000/v1/chat/completions \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $$(grep LITELLM_MASTER_KEY .env | cut -d= -f2)" \
		-d "{\"model\":\"$(MODEL)\",\"messages\":[{\"role\":\"user\",\"content\":\"$(MSG)\"}]}" \
		| python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

clean: ## Remove containers (keeps no persistent volumes)
	@docker compose down
	@echo "✅ Cleaned up"

help: ## Show this help
	@echo ""
	@echo "🔀 LiteLLM Service Commands"
	@echo "==========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Examples:"
	@echo "    make up                          # Start service"
	@echo "    make test                        # Validate endpoints"
	@echo "    make model-claude                # Switch to Claude"
	@echo "    make chat MODEL=fast MSG='hello' # Quick test"
	@echo "    make logs                        # Follow logs"
	@echo ""
