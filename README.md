# 🤖 AI Dev Platform

> Stop managing AI tools. Start managing AI outcomes.

**A portable, provider-agnostic AI development environment for developers who build serious things.**

One stable interface. Any AI agent. Any compute. Anywhere.

---

## 🧠 Core Principle

> **Only one thing is stable: the AI interface.**
> Everything else can change, will change, should be replaceable.

```
Developer
    │
    ▼
./ai run "your task"              ← Stable CLI — never changes
    │
    ▼
scripts/runtime.sh (v8.5)         ← Execution engine + trace logging
    │
    ▼
scripts/adapters/agent.sh         ← Shim → agent.py
    │
    ▼
scripts/agent.py (v8.6)           ← Deterministic agent loop
    │
    ▼
scripts/router.py (v6.1)          ← Intent → deterministic plan
    │
    ▼
scripts/tool_executor.py          ← MCP-compliant plugin engine
    │
    ▼
scripts/tools/*.py                ← Tool plugins
```

Swap the model. Swap the compute. Swap the adapter.
**Your workflow never changes.**

---

## ✨ Features

- **Deterministic Planning** — `router.py` converts intent to a structured tool execution plan — no LLM guessing required for well-known tasks
- **Provider Agnostic** — LiteLLM routes to Ollama, OpenAI, Anthropic/Claude, NVIDIA NIM, or Colab GPU
- **Tier-Based Routing** — `fast` / `balanced` / `heavy` model tiers map automatically to command type
- **Run Persistence** — Every run stored in `runs/<run_id>/` with `trace.json` and `result.json`
- **Structured Trace Logging** — Per-session NDJSON traces in `logs/traces/` with `tool_call` + `tool_result` events
- **Scenario-Driven Evaluation** — Run scenarios, score traces, pass/fail against structured criteria
- **MCP-Compliant Tools** — Plugin system with OpenAI function schema export for LLM tool-calling
- **Log Management** — `log_manager.py` handles trace rotation, run retention, and disk cleanup
- **Portable** — Unified Dev Container — clone, open, done
- **Offline Mode** — Mock adapter works with zero network
- **Agent Skills** — SKILL.md context files for Goose and Claude on all managed projects

---

## 🚀 Quick Start

### Option 1 — Dev Container (Recommended)

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code → **Reopen in Container**

Everything builds automatically — Ollama pulls tinyllama, LiteLLM starts, environment configures. First run takes ~3 minutes.

```bash
make status
make health
./ai run "say hello"
```

### Option 2 — Manual Setup

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
make setup
./scripts/switch-model.sh litellm-fast
./ai run "say hello"
```

---

## 📋 Requirements

| Tool | Required | Notes |
|------|----------|-------|
| Docker | ✅ Yes | Dev Container + Ollama + LiteLLM services |
| VS Code | ✅ Yes | With Dev Containers extension |
| Goose CLI | Optional | `make install-goose` — only needed for Goose adapter mode |
| OpenAI API Key | Optional | Enables `heavy` tier (gpt-4.1) |
| Anthropic API Key | Optional | Enables `heavy` tier (claude-sonnet) |
| NVIDIA NIM API Key | Optional | Free at build.nvidia.com — enables `balanced` tier |

---

## ⚡ The `ai` Command

Everything flows through one stable interface:

```bash
ai run      "create a file called hello.txt with content 'hi'"
ai fix      "ImportError in agent_runner.py line 42"
ai explain  "how does Q-learning convergence work"
ai refactor "simplify the env_interface adapter"
ai query    "what should I build next"

# Global flags
ai --trace run "debug this"          # enable per-session trace logging
ai --model=heavy run "complex task"  # override model tier
ai --adapter=mock run "offline"      # override adapter
```

**Same commands. Any backend. Any environment.**

---

## 🧠 How Routing Works

`router.py` converts user input into a deterministic execution plan:

```
"create a file called hello.txt with content 'hi' and then list files"
    │
    ▼ router.py (deterministic planner)
    │
    ├── step 1: write_file  {"path": "hello.txt", "content": "hi"}
    └── step 2: list_files  {"path": "."}
```

For unrecognized tasks, the router falls back to the LLM agent via LiteLLM. Commands auto-map to model tiers:

| Command | Tier | Primary Model |
|---------|------|---------------|
| `query` | fast | tinyllama (local) |
| `explain` | balanced | DeepSeek R1 (NVIDIA NIM) → tinyllama |
| `fix` | heavy | gpt-4.1 → claude-sonnet → tinyllama |
| `run` | heavy | gpt-4.1 → claude-sonnet → tinyllama |
| `refactor` | heavy | gpt-4.1 → claude-sonnet → tinyllama |

---

## 🔄 Switching Providers

```bash
./scripts/switch-model.sh litellm-fast      # tinyllama local
./scripts/switch-model.sh litellm-balanced  # NVIDIA NIM → tinyllama fallback
./scripts/switch-model.sh litellm-code      # gpt-4.1 → tinyllama fallback
./scripts/switch-model.sh litellm-claude    # claude-sonnet → tinyllama fallback
./scripts/switch-model.sh litellm-smart     # best available model
./scripts/switch-model.sh mock              # offline — no AI calls
./scripts/switch-model.sh colab             # Google Colab GPU via ngrok
```

---

## 📁 Project Structure

```
ai-dev-platform/
├── ai                              ← ⭐ Stable CLI (v1.1)
├── ai-eval                         ← Evaluation CLI
├── .devcontainer/
│   ├── docker-compose.yml          ← Unified stack (devcontainer + ollama + litellm)
│   ├── Dockerfile                  ← Ubuntu 22.04 + Python + Docker CLI + Goose
│   ├── goose-config.sh
│   └── post-create.sh
├── scripts/
│   ├── runtime.sh                  ← Execution engine (v8.5)
│   ├── agent.py                    ← Agent loop (v8.6) — deterministic planner
│   ├── router.py                   ← Intent → plan (v6.1)
│   ├── tool_executor.py            ← Plugin engine (v3.3)
│   ├── tool_executor.sh            ← Thin bash wrapper
│   ├── run_scenario.sh             ← Scenario runner (v3.2)
│   ├── run_scenario.py             ← Scenario loader (v2)
│   ├── switch-model.sh             ← Provider switching (v7.0)
│   ├── health-check.sh             ← System health
│   ├── start-colab-proxy.sh        ← Colab GPU setup
│   ├── compare.sh                  ← Model comparison runner
│   ├── regression.sh               ← Regression runner
│   ├── debug_routing.sh            ← Routing debug helper
│   ├── adapters/
│   │   ├── _base.sh                ← Shared contract utilities (v8)
│   │   ├── agent.sh                ← Shim → agent.py (v9)
│   │   ├── goose.sh                ← Goose adapter
│   │   ├── mock.sh                 ← Offline adapter
│   │   └── agents/                 ← Per-command agent YAML configs
│   │       ├── default.yaml
│   │       ├── explain.yaml
│   │       ├── fix.yaml
│   │       └── query.yaml
│   ├── tools/                      ← Tool plugins (MCP-compliant)
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── list_files.py
│   │   ├── run_bash.py
│   │   ├── http_get.py
│   │   ├── read_trace.py
│   │   ├── evaluate_trace.py       ← Structured criteria evaluator (v2.0)
│   │   └── compare_results.py
│   ├── lib/
│   │   └── trace_logger.py         ← Per-session NDJSON trace logger
│   ├── mock-server/                ← Local OpenAI-compatible test server
│   └── tests/
│       ├── tool_test_v2.sh         ← Tool + agent + runtime tests (14/14)
│       ├── test_adapters.sh        ← Adapter validation (10/10)
│       ├── runtime_tests.sh        ← Runtime stability tests (6/6)
│       ├── goose_tests.sh
│       ├── tool_test.sh
├── ollama-service/                 ← Ollama container (tinyllama)
├── litellm-service/                ← LiteLLM router container
│   └── config.yaml                 ← Tier routing (fast/balanced/heavy)
├── scenarios/
│   ├── agent-sim/
│   ├── arb-agent-system/
│   └── tests/
├── evals/
│   └── results/                    ← Scored evaluation results (JSON)
├── runs/                           ← Per-run storage (trace.json + result.json)
├── logs/
│   ├── traces/                     ← Per-session NDJSON trace logs
│   └── evals/                      ← Per-run eval records
├── skills/                         ← Agent Skills (Goose/Claude context)
│   ├── agent-sim/SKILL.md
│   ├── arb-agent-system/SKILL.md
│   ├── private-ai-stack/SKILL.md
│   └── ai-dev-platform/SKILL.md
├── Makefile
└── .env.example
```

---

## 🧪 Test Suite

```bash
# Full suite
./scripts/tests/tool_test_v2.sh    # 14/14 — tool + agent + runtime
./scripts/tests/test_adapters.sh   # 10/10 — adapter validation
./scripts/tests/runtime_tests.sh   #  6/6  — runtime stability
```

All tests pass against live LiteLLM when reachable — skip gracefully when offline.

---

## 📊 Scenario Evaluation

```bash
./scripts/run_scenario.sh scenarios/tests/test_list_files_v3.json --model=fast

# 📘 Loading scenario...
# 🚀 Running scenario...
# 🎯 SCORE: 1
# ✅ Scenario passed
```

Criteria types:
```json
{"type": "tool_used",       "tool": "write_file"}
{"type": "no_errors"}
{"type": "output_contains", "value": "hello"}
```

Results saved to `evals/results/`. Run data saved to `runs/<run_id>/`.

---

## 🧹 Log Management

```bash
# Clean up old traces and runs
python3 scripts/lib/log_manager.py

# Protect current trace from cleanup
python3 scripts/lib/log_manager.py --protect logs/traces/ai_trace.*.log

# Dry run (preview what would be removed)
AI_LOG_DRY_RUN=1 python3 scripts/lib/log_manager.py
```

Configurable via environment:
```bash
AI_LOG_MAX_FILES=50        # max trace files to keep
AI_LOG_MAX_SIZE_MB=5       # max file size before truncation
AI_MAX_RUN_DIRS=50         # max run directories to keep
AI_RUN_RETENTION_SEC=86400 # run retention in seconds (default: 24h)
```

---

## 🔌 Adding Your Own Tool

Drop a Python file in `scripts/tools/`:

```python
# scripts/tools/my_tool.py
name = "my_tool"
description = "Does something useful"
input_schema = {
    "type": "object",
    "properties": {
        "input": {"type": "string", "description": "The input"}
    },
    "required": ["input"]
}

def run(input_data):
    result = do_something(input_data.get("input"))
    return {
        "status": "success",
        "data": result,
        "error": None,
        "meta": {"tool": "my_tool"}
    }
```

Auto-discovered on next run. No registration needed.

---

## 🔌 Adding Your Own Adapter

```bash
#!/bin/bash
# scripts/adapters/my-agent.sh

ADAPTER_NAME="my-agent"
source "$(dirname "$0")/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

case "$COMMAND" in
  run|fix|explain|refactor|query)
    RESPONSE=$(my_agent_cli "$INPUT")
    build_response "done" "$RESPONSE"
    adapter_exit
    ;;
  *)
    build_response "error" "Unknown command: $COMMAND" "invalid_request"
    adapter_exit
    ;;
esac
```

```bash
chmod +x scripts/adapters/my-agent.sh
AI_ADAPTER=my-agent ./ai run "test"
```

**The interface is stable. Everything behind it is replaceable.**

---

## 🗺️ Roadmap

- [x] Stable `ai` CLI (v1.1)
- [x] Runtime v8.5 — per-session trace logging to `logs/traces/`
- [x] Deterministic planner — `router.py` converts intent to tool plan
- [x] Agent loop v8.6 — run persistence in `runs/`
- [x] `TraceLogger` — structured NDJSON with `tool_call` + `tool_result` events
- [x] `log_manager.py` — automated trace + run cleanup
- [x] LiteLLM tier routing (fast/balanced/heavy)
- [x] MCP-compliant tool plugin system with OpenAI schema export
- [x] `evaluate_trace` — structured criteria evaluator
- [x] 30/30 tests passing across all test suites
- [x] Unified Dev Container (devcontainer + ollama + litellm)
- [x] Agent Skills for all managed projects
- [x] NVIDIA NIM free tier integration
- [ ] Persistent sessions across container restarts
- [ ] Multi-project registry (`make register PROJECT=...`)
- [ ] Web UI control panel
- [ ] CI/CD integration guide (GitHub Actions)
- [ ] Router coverage expansion (more matchers)
- [ ] Multi-user team configuration

---

## 🙏 Acknowledgments

- [LiteLLM](https://github.com/BerriAI/litellm) — Universal LLM router
- [Goose](https://block.github.io/goose/) — AI agent by Block
- [Ollama](https://ollama.ai/) — Local LLM runtime
- [NVIDIA NIM](https://build.nvidia.com) — Free-tier cloud inference
- [agent-sim](https://github.com/sparky10001/agent-sim) — LLM-native RL framework
- [private-ai-stack](https://github.com/sparky10001/private-ai-stack) — Local AI infrastructure

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
Built with ❤️ by James R. Glines<br>
The interface is stable. Everything else is replaceable.
</p>