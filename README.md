# 🤖 AI Dev Platform

> Stop managing AI tools. Start managing AI outcomes.

**A portable, provider-agnostic AI development environment for developers who build serious things.**

One stable interface. Any AI agent. Any compute. Anywhere.

---

## 🧠 Core Principle# 🤖 AI Dev Platform

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
./ai run "your task"          ← Stable CLI — never changes
    │
    ▼
scripts/runtime.sh            ← Execution engine + per-session trace logging
    │
    ▼
scripts/router.py             ← Intent classification → model tier
    │
    ▼
scripts/adapters/agent.sh     ← Active adapter (agent | goose | mock)
    │
    ▼
scripts/agent.py              ← LiteLLM agent loop + tool execution
    │
    ▼
LiteLLM (http://litellm:4000) ← Universal router
    │
    ▼
Ollama │ OpenAI │ Claude │ NVIDIA NIM   ← Replaceable compute
```

Swap the adapter. Swap the model. Swap the compute.
**Your workflow never changes.**

---

## ✨ Features

- **Provider Agnostic** — LiteLLM routes to Ollama, OpenAI, Anthropic/Claude, NVIDIA NIM, or fully offline mock
- **Intent-Based Routing** — command type maps automatically to the right model tier (fast / balanced / heavy)
- **Tool-Using Agent** — native OpenAI function-calling loop with 9 built-in tools
- **Simulation-Driven CI** — scenario specs, trace evaluation, and automated scoring
- **Portable** — unified Docker stack, works on any machine or on a plane
- **Project Aware** — inject context for agent-sim, arb-agent-system, private-ai-stack
- **Fully Tested** — 14-test suite covering tools, agent, and runtime layers
- **Offline Mode** — mock adapter works without internet

---

## 🚀 Quick Start

### Option 1 — Dev Container (Recommended)

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code → **Reopen in Container**

The unified Docker stack builds automatically — Ollama pulls tinyllama, LiteLLM starts, environment configures itself.

```bash
make status          # verify active configuration
make health          # check all services
./ai run "hello"     # test the full chain
```

### Option 2 — Local Setup

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
make setup
make litellm-fast    # local tinyllama via LiteLLM
./ai run "hello"
```

---

## 📋 Requirements

| Tool | Required | Notes |
|------|----------|-------|
| Docker | ✅ Yes | Unified dev stack |
| VS Code | ✅ Yes | With Dev Containers extension |
| OpenAI API Key | Optional | `litellm-code` / `litellm-heavy` |
| Anthropic API Key | Optional | `litellm-claude` / `litellm-heavy` |
| NVIDIA NIM API Key | Optional | `litellm-balanced` (free at build.nvidia.com) |
| Goose CLI | Optional | `make install-goose` |

---

## ⚡ The `ai` Command

Everything flows through one stable interface:

```bash
ai run      "analyze the agent-sim protocol layer"
ai fix      "ImportError in agent_runner.py line 42"
ai explain  "how does Q-learning convergence work"
ai refactor "simplify the env_interface adapter"
ai query    "what should I build next"
```

**Same commands. Any backend. Any environment.**

Flags:
```bash
./ai run "task" --trace          # enable per-session trace logging
./ai run "task" --model=heavy    # override model tier
./ai --adapter=mock run "task"   # override adapter
```

---

## 🧠 Model Tiers

Commands map automatically to model tiers. LiteLLM handles routing and fallback:

| Tier | Command | Primary | Fallback | Use When |
|------|---------|---------|----------|----------|
| `fast` | `query` | tinyllama (local) | — | Quick queries, always available |
| `balanced` | `explain` | NVIDIA NIM DeepSeek-R1 | tinyllama | Efficient reasoning |
| `heavy` | `run`, `fix`, `refactor` | gpt-4.1 → claude-sonnet | tinyllama | Complex tasks |

Override with:
```bash
./ai run "task" --model=fast     # force local
./ai run "task" --model=heavy    # force best available
ACTIVE_MODEL=balanced ./ai run "task"
```

---

## 🔄 Switching Providers

```bash
# LiteLLM tiers (recommended)
make litellm-fast      # tinyllama local — always available, no keys
make litellm-balanced  # NVIDIA NIM — free, strong reasoning
make litellm-code      # gpt-4.1 cloud
make litellm-claude    # claude-sonnet cloud
make litellm-heavy     # best available (gpt-4.1 → claude → tinyllama)

# Direct adapters
make mock              # offline — no AI calls
make mock-local        # Goose → local mock OpenAI server

# GPU
make colab             # Google Colab GPU via ngrok
```

---

## 🌍 Environment Scenarios

### 🏠 At Home — Private Local AI
```bash
make litellm-fast
make ctx-agent-sim
./ai run "review the Q-learning convergence issue"
# tinyllama runs locally — no data leaves your network
```

### ☁️ At Work — Cloud Intelligence
```bash
make litellm-heavy
make ctx-arb
./ai run "refactor the risk service"
# gpt-4.1 via LiteLLM — falls back to tinyllama if key missing
```

### ✈️ On a Plane — Offline
```bash
make mock
./ai run "plan the next sprint"
# → [MOCK] Would run: plan the next sprint
# No internet required
```

### 🖥️ Need GPU — Google Colab
```bash
make colab
./ai run "train Q-agent for 10000 episodes"
# Routes to Colab GPU via ngrok
```

---

## 📁 Project Structure

```
ai-dev-platform/
├── ai                              ← ⭐ Stable CLI (v1.1)
├── ai-eval                         ← Evaluation CLI
├── .devcontainer/
│   ├── docker-compose.yml          ← Unified stack (devcontainer + ollama + litellm)
│   ├── Dockerfile                  ← Dev environment
│   ├── goose-config.sh
│   └── post-create.sh              ← Auto-starts Ollama + LiteLLM
├── scripts/
│   ├── runtime.sh                  ← Execution engine (v7.4) + per-session traces
│   ├── router.py                   ← Intent → model tier classification
│   ├── agent.py                    ← LiteLLM agent loop (v3.3)
│   ├── tool_executor.py            ← Python tool engine (v3.3)
│   ├── tool_executor.sh            ← Shell wrapper
│   ├── run_scenario.sh             ← Scenario execution + evaluation (v5.0)
│   ├── compare.sh                  ← Model comparison runner
│   ├── regression.sh               ← Regression test runner
│   ├── health-check.sh             ← System health
│   ├── switch-model.sh             ← Provider switching (v6.0)
│   ├── start-colab-proxy.sh        ← Colab GPU setup
│   ├── adapters/
│   │   ├── _base.sh                ← Shared contract utilities (v8)
│   │   ├── agent.sh                ← agent.py shim (primary adapter)
│   │   ├── goose.sh                ← Goose agent adapter
│   │   └── mock.sh                 ← Offline adapter
│   ├── tools/                      ← Tool plugins (MCP-compatible)
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── list_files.py
│   │   ├── run_bash.py
│   │   ├── http_get.py
│   │   ├── read_trace.py
│   │   ├── run_scenario.py
│   │   ├── evaluate_trace.py       ← Structured criteria evaluation (v5.0)
│   │   └── compare_results.py
│   ├── mock-server/                ← Local OpenAI-compatible test server
│   └── tests/
│       └── tool_test.sh                 ← 14-test validation suite (v1.2)
├── ollama-service/                 ← Ollama container (tinyllama)
├── litellm-service/                ← LiteLLM router (v2.3 config)
│   └── config.yaml                 ← Tier routing: fast/balanced/heavy
├── scenarios/                      ← Evaluation scenario specs
│   ├── agent-sim/                  ← GridWorld, protocol, LLM benchmark
│   ├── arb-agent-system/           ← Health, spread detection, data validation
│   └── tests/                      ← Platform self-tests
├── evals/
│   └── results/                    ← Saved evaluation results (JSON)
├── skills/                         ← Agent Skills context files
│   ├── agent-sim/SKILL.md
│   ├── arb-agent-system/SKILL.md
│   ├── private-ai-stack/SKILL.md
│   └── ai-dev-platform/SKILL.md
├── Makefile                        ← Unified control surface
└── .env.example
```

---

## 🧰 Tool System

The agent has 9 built-in tools, auto-discovered at runtime:

| Tool | Description |
|------|-------------|
| `read_file` | Read any workspace file |
| `write_file` | Write files with path traversal protection |
| `list_files` | Directory listing with type metadata |
| `run_bash` | Execute shell commands in workspace |
| `http_get` | HTTP GET with JSON auto-detection |
| `read_trace` | Parse per-session AI trace logs |
| `run_scenario` | Load and validate scenario specs |
| `evaluate_trace` | Score trace against structured criteria |
| `compare_results` | Compare evaluation runs |

Tools follow MCP format and are auto-exported as OpenAI function schemas.

---

## 🧪 Scenario-Driven Evaluation

Run agent tasks against defined success criteria:

```bash
# Run a scenario
./scripts/run_scenario.sh scenarios/tests/test_list_files_v2.json --model=balanced

# Output:
# 🔍 Tools called: write_file, list_files
# 🎯 SCORE: 1
# ✅ Scenario passed
# 📁 Saved → evals/results/test_list_files_v2_20260502T170417Z.json
```

Scenario spec format:
```json
{
  "scenario_id": "my_scenario",
  "task": "Create a file and list directory",
  "success_criteria": [
    {"type": "tool_used", "tool": "write_file"},
    {"type": "tool_used", "tool": "list_files"},
    {"type": "no_errors"}
  ]
}
```

Supported criterion types: `tool_used`, `no_errors`, `output_contains`

---

## 🧪 Test Suite

```bash
./scripts/tests/tool_test_v2.sh
```

Runs 14 tests across tool, agent, and runtime layers:
```
📦 Tool Layer (9 tests)   — no LiteLLM required
🤖 Agent + Runtime (3 tests) — skipped gracefully if LiteLLM offline
```

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
  run)      MY_RESPONSE=$(my_agent "$INPUT") ;;
  fix)      MY_RESPONSE=$(my_agent "Fix: $INPUT") ;;
  explain)  MY_RESPONSE=$(my_agent "Explain: $INPUT") ;;
  refactor) MY_RESPONSE=$(my_agent "Refactor: $INPUT") ;;
  query)    MY_RESPONSE=$(my_agent "$INPUT") ;;
  *)
    build_response "error" "Unknown command: $COMMAND" "invalid_request"
    adapter_exit
    ;;
esac

build_response "done" "$MY_RESPONSE"
adapter_exit
```

```bash
chmod +x scripts/adapters/my-agent.sh
AI_ADAPTER=my-agent ./ai run "test"
```

**The interface is stable. Everything behind it is replaceable.**

---

## 🗺️ Roadmap

- [x] Stable `ai` CLI (v1.1)
- [x] Runtime v7.4 with per-session trace logging
- [x] LiteLLM tier routing (fast / balanced / heavy)
- [x] LiteLLM v2.3 config (NVIDIA NIM + OpenAI + Anthropic + Ollama)
- [x] agent.py v3.3 — native tool-calling loop
- [x] 9-tool MCP-compatible plugin system
- [x] Scenario-driven evaluation with structured criteria
- [x] 14-test validation suite
- [x] Unified Docker stack (devcontainer + ollama + litellm)
- [x] Agent Skills for all managed projects
- [x] Goose adapter
- [x] Mock offline adapter
- [ ] Persistent sessions across container restarts
- [ ] Multi-project registry (`make register PROJECT=...`)
- [ ] Web UI control panel
- [ ] CI/CD integration guide
- [ ] NVIDIA NIM adapter (direct, without LiteLLM)

---

## 🙏 Acknowledgments

- [LiteLLM](https://github.com/BerriAI/litellm) — Universal LLM router
- [Ollama](https://ollama.ai/) — Local LLM runtime
- [Goose](https://block.github.io/goose/) — AI agent by Block
- [NVIDIA NIM](https://build.nvidia.com/) — Free GPU inference API
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