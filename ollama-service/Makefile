###################################################################
# Ollama Service — Makefile
###################################################################

.PHONY: up down build logs shell test pull status clean help
.DEFAULT_GOAL := help

up: ## Build and start Ollama service
	@echo "🦙 Starting Ollama service..."
	docker compose up --build -d
	@echo "⏳ Waiting for service to be ready..."
	@sleep 5
	@make status

down: ## Stop Ollama service
	@docker compose down
	@echo "✅ Ollama service stopped"

build: ## Build image only (no start)
	@docker compose build

logs: ## Follow service logs
	@docker compose logs -f ollama

shell: ## Open shell in running container
	@docker exec -it ollama /bin/bash

test: ## Run validation tests
	@echo "🧪 Running Ollama validation tests..."
	@docker compose --profile test up --abort-on-container-exit ollama-test

pull: ## Pull a model (MODEL=phi3)
	@if [ -z "$(MODEL)" ]; then \
		echo "Usage: make pull MODEL=phi3"; \
	else \
		docker exec ollama ollama pull $(MODEL); \
	fi

status: ## Show service status and available models
	@echo ""
	@echo "📊 Ollama Service Status"
	@echo "========================"
	@docker compose ps
	@echo ""
	@echo "📋 Available models:"
	@docker exec ollama ollama list 2>/dev/null || echo "   (service not running)"
	@echo ""

clean: ## Remove containers and volume (WARNING: deletes downloaded models!)
	@echo "⚠️  This will delete all downloaded models!"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker compose down -v
	@echo "✅ Cleaned up"

help: ## Show this help
	@echo ""
	@echo "🦙 Ollama Service Commands"
	@echo "=========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Examples:"
	@echo "    make up                  # Start service"
	@echo "    make test                # Validate endpoints"
	@echo "    make pull MODEL=phi3     # Add a model"
	@echo "    make logs                # Follow logs"
	@echo ""
