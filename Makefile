###################################################################
# AI Dev Platform — Makefile (v9.1 LiteLLM-first, Phase 3E runtime aligned)
#
# Key Improvements:
# - Fully aligned with switch-model.sh v6.0
# - LiteLLM is the single gateway
# - Goose = runtime adapter only
# - Removed invalid/legacy providers (local/http-agent/etc.)
# - Hardened validation + mock lifecycle
# - Backwards-compatible env handling
# - Added Phase 3E runtime validation ladder
###################################################################

.PHONY: setup install-goose \
        litellm goose colab mock mock-local \
        mock-server mock-server-bg mock-server-stop mock-server-test \
        fallback-dev fallback-prod \
        profile-fast profile-agent profile-offline profile-local profile \
        litellm-fast litellm-code litellm-claude \
        health status validate \
        runtime-tests runtime-test-core runtime-test-phase3 runtime-test-all runtime-snapshot-tests runtime-adapter-gateway-tests runtime-run-lifecycle-tests runtime-trace-pipeline-tests runtime-replay-ledger-tests runtime-eval-ledger-tests runtime-registry-ledger-tests runtime-ledger-authoritative-tests \
        control-plane-dag-tests control-plane-tool-tests control-plane-executor-tests control-plane-trace-tests control-plane-planner-tests control-plane-orchestrator-tests control-plane-cli-tests control-plane-policy-tests control-plane-scenario-tests control-plane-replay-tests control-plane-eval-tests control-plane-experiment-tests control-plane-benchmark-tests control-plane-strategy-tests control-plane-heuristic-tests control-plane-memory-tests control-plane-tests \
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
	@chmod +x scripts/tests/*.sh 2>/dev/null || true
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
# Runtime Test Ladder
###################################################################

runtime-test-core:
	@echo ""
	@echo "🧪 Runtime core tests"
	@AI_ADAPTER=agent ./scripts/tests/runtime_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/failure_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/ndjson_integrity_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/event_ordering_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/replayability_smoke_test.sh
	@AI_ADAPTER=agent ./scripts/tests/run_structure_test.sh
	@AI_ADAPTER=agent ./scripts/tests/trace_schema_consistency_test.sh
	@AI_ADAPTER=agent ./scripts/tests/parallel_run_isolation_test.sh
	@AI_ADAPTER=agent ./scripts/tests/resume_from_trace_tests.sh

runtime-snapshot-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_snapshot_tests.sh
runtime-adapter-gateway-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_adapter_gateway_tests.sh
runtime-run-lifecycle-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_run_lifecycle_tests.sh
runtime-trace-pipeline-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_trace_pipeline_tests.sh
runtime-event-ledger-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_event_ledger_tests.sh
runtime-replay-ledger-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_replay_ledger_tests.sh
runtime-eval-ledger-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_eval_ledger_tests.sh
runtime-registry-ledger-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_registry_ledger_tests.sh
runtime-ledger-authoritative-tests:
	@AI_ADAPTER=agent ./scripts/tests/runtime_ledger_authoritative_tests.sh


runtime-test-phase3:
	@echo ""
	@echo "🧪 Runtime Phase 3 tests"
	@AI_ADAPTER=agent ./scripts/tests/loader_replay_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_eval_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_registry_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_dataset_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_contract_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_snapshot_tests.sh
	@AI_ADAPTER=agent ./scripts/tests/runtime_trace_pipeline_tests.sh
	@$(MAKE) runtime-event-ledger-tests --no-print-directory
	@$(MAKE) runtime-replay-ledger-tests --no-print-directory
	@$(MAKE) runtime-eval-ledger-tests --no-print-directory
	@$(MAKE) runtime-registry-ledger-tests --no-print-directory
	@$(MAKE) runtime-ledger-authoritative-tests --no-print-directory
	@$(MAKE) runtime-adapter-gateway-tests --no-print-directory
	@$(MAKE) runtime-run-lifecycle-tests --no-print-directory

runtime-tests runtime-test-all: runtime-test-core runtime-test-phase3
	@echo ""
	@echo "🎉 Full runtime test ladder passed"

###################################################################
# Control-Plane Test Ladder (Stage 4, isolated)
###################################################################

control-plane-dag-tests:
	@./scripts/tests/control_plane_dag_tests.sh

control-plane-tool-tests:
	@./scripts/tests/control_plane_tool_registry_tests.sh

control-plane-executor-tests:
	@./scripts/tests/control_plane_dag_executor_tests.sh

control-plane-trace-tests:
	@./scripts/tests/control_plane_trace_bridge_tests.sh

control-plane-planner-tests:
	@./scripts/tests/control_plane_planner_tests.sh

control-plane-orchestrator-tests:
	@./scripts/tests/control_plane_orchestrator_tests.sh

control-plane-cli-tests:
	@./scripts/tests/control_plane_cli_tests.sh

control-plane-policy-tests:
	@./scripts/tests/control_plane_policy_tests.sh

control-plane-scenario-tests:
	@./scripts/tests/control_plane_scenario_tests.sh

control-plane-replay-tests:
	@./scripts/tests/control_plane_replay_tests.sh

control-plane-eval-tests:
	@./scripts/tests/control_plane_eval_tests.sh

control-plane-experiment-tests:
	@./scripts/tests/control_plane_experiment_tests.sh

control-plane-benchmark-tests:
	@./scripts/tests/control_plane_benchmark_tests.sh

control-plane-strategy-tests:
	@./scripts/tests/control_plane_strategy_tests.sh

control-plane-heuristic-tests:
	@./scripts/tests/control_plane_heuristic_tests.sh

control-plane-memory-tests:
	@./scripts/tests/control_plane_memory_tests.sh

control-plane-knowledge-tests:
	@./scripts/tests/control_plane_knowledge_tests.sh

control-plane-graph-analytics-tests:
	@./scripts/tests/control_plane_graph_analytics_tests.sh

control-plane-parallel-tests:
	@./scripts/tests/control_plane_parallel_executor_tests.sh

control-plane-tests:
	@$(MAKE) control-plane-dag-tests --no-print-directory
	@$(MAKE) control-plane-tool-tests --no-print-directory
	@$(MAKE) control-plane-executor-tests --no-print-directory
	@$(MAKE) control-plane-trace-tests --no-print-directory
	@$(MAKE) control-plane-planner-tests --no-print-directory
	@$(MAKE) control-plane-orchestrator-tests --no-print-directory
	@$(MAKE) control-plane-cli-tests --no-print-directory
	@$(MAKE) control-plane-policy-tests --no-print-directory
	@$(MAKE) control-plane-scenario-tests --no-print-directory
	@$(MAKE) control-plane-replay-tests --no-print-directory
	@$(MAKE) control-plane-eval-tests --no-print-directory
	@$(MAKE) control-plane-experiment-tests --no-print-directory
	@$(MAKE) control-plane-benchmark-tests --no-print-directory
	@$(MAKE) control-plane-strategy-tests --no-print-directory
	@$(MAKE) control-plane-heuristic-tests --no-print-directory
	@$(MAKE) control-plane-memory-tests --no-print-directory
	@$(MAKE) control-plane-knowledge-tests --no-print-directory
	@$(MAKE) control-plane-graph-analytics-tests --no-print-directory
	@$(MAKE) control-plane-parallel-tests --no-print-directory
	
###################################################################
# Validation Ladder (HARDENED)
###################################################################

validate:
	@echo "🪜 Validation ladder"
	@echo ""

	@echo "Step 1 — Mock (offline)"
	@$(MAKE) mock --no-print-directory
	@AI_ADAPTER=agent ./scripts/runtime.sh run "ping" | jq -e '.status == "done"' >/dev/null && echo "✅ Runtime OK" || (echo "❌ Runtime failed"; exit 1)

	@echo ""
	@echo "Step 1b — Runtime test ladder"
	@$(MAKE) runtime-tests --no-print-directory

	@echo ""
	@echo "Step 2 — Mock server (OpenAI-compatible)"
	@$(MAKE) mock-server-bg --no-print-directory
	@$(MAKE) mock-local --no-print-directory
	@AI_ADAPTER=agent ./scripts/runtime.sh run "ping" && echo "✅ Mock API OK" || (echo "❌ Mock API failed"; exit 1)
	@$(MAKE) mock-server-stop --no-print-directory

	@echo ""
	@echo "Step 3 — LiteLLM"
	@$(MAKE) litellm --no-print-directory
	@curl -s \
	  -H "Authorization: Bearer $${LITELLM_MASTER_KEY:-ai-dev-platform}" \
	  http://litellm:4000/v1/models \
	  | jq -e '.data | length > 0' >/dev/null \
	  && echo "✅ LiteLLM OK" \
	  || echo "⚠️ LiteLLM unavailable"
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
	@echo "  make validate         # Run provider + runtime validation ladder"
	@echo "  make runtime-tests    # Run full runtime test ladder"
	@echo "  make status"
	@echo ""

.PHONY: runtime-event-ledger-tests runtime-replay-ledger-tests runtime-eval-ledger-tests runtime-registry-ledger-tests runtime-ledger-authoritative-tests
