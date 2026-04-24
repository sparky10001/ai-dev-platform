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
./ai run "your task"          ← Stable CLI — never changes
    │
    ▼
scripts/runtime.sh            ← Execution engine + trace logging
    │
    ▼
scripts/router.sh             ← Intent classification + normalization
    │
    ▼
LiteLLM │ Goose │ Mock        ← Swappable adapters
    │
    ▼
Ollama │ OpenAI │ Claude │ Colab   ← Replaceable compute
```

Swap the adapter. Swap the model. Swap the compute.
**Your workflow never changes.**

---

## ✨ Features

- **Provider Agnostic** — LiteLLM, OpenAI, Anthropic/Claude, Colab GPU, local Ollama, or fully offline mock
- **Agent Agnostic** — Goose today, anything tomorrow via the adapter contract
- **Portable** — Works in Dev Containers, bare metal, CI/CD, or on a plane
- **Intent-Based Routing** — LiteLLM maps task type to the right model automatically
- **Project Aware** — Switch context between agent-sim, arb-agent-system, private-ai-stack
- **Health Verified** — Full system validation with `make health`
- **Offline Mode** — Fully functional without internet via mock adapter
- **Evaluation Ready** — Built-in `ai-eval` CLI for simulation-driven CI

---

## 🚀 Quick Start

### Option 1 — Dev Container (Recommended)

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code → **Reopen in Container**

Everything builds automatically — Ollama pulls tinyllama, LiteLLM starts, environment configures itself.

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
| Docker | ✅ Yes | Dev Container + service stack |
| VS Code | ✅ Yes | With Dev Containers extension |
| Goose CLI | Optional | `make install-goose` |
| OpenAI API Key | Optional | For `litellm-code` / `litellm-smart` |
| Anthropic API Key | Optional | For `litellm-claude` / `litellm-smart` |

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

---

## 🔄 Switching Providers

```bash
# LiteLLM (recommended — intent-based routing)
make litellm-fast      # tinyllama local — always available
make litellm-code      # gpt-4.1 → tinyllama fallback
make litellm-claude    # claude-sonnet → tinyllama fallback
make litellm-smart     # best available model

# Direct adapters
make goose             # Goose AI agent (OpenAI backend)
make mock              # Offline mode — no AI calls
make mock-local        # Local mock OpenAI server

# GPU
make colab             # Google Colab GPU via ngrok
```

Or via environment override:
```bash
ACTIVE_MODEL=claude make ai-run CMD="complex reasoning task"
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
make litellm-code
make ctx-arb
./ai run "refactor the risk service"
# gpt-4.1 via LiteLLM — falls back to tinyllama if key missing
```

### ✈️ On a Plane — Offline
```bash
make mock
./ai run "plan the LiteLLM integration architecture"
# → [MOCK] Would run: plan the LiteLLM integration...
# No internet required
```

### 🖥️ Need GPU — Google Colab
```bash
make colab
./ai run "train Q-agent for 10000 episodes"
# LiteLLM routes to Colab GPU via ngrok
```

---

## 📁 Project Structure

```
ai-dev-platform/
├── ai                         ← ⭐ Stable CLI interface
├── ai-eval                    ← Evaluation CLI
├── .devcontainer/
│   ├── docker-compose.yml     ← Unified stack (devcontainer + ollama + litellm)
│   ├── Dockerfile             ← Dev environment
│   ├── goose-config.sh
│   └── post-create.sh
├── scripts/
│   ├── runtime.sh             ← Execution engine (v5.7)
│   ├── router.sh              ← Intent router (v3.2)
│   ├── tool_executor.sh       ← Tool dispatch wrapper
│   ├── tool_executor.py       ← Python tool engine (v3.1)
│   ├── tools/                 ← Tool plugins
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── list_files.py
│   │   ├── run_bash.py
│   │   ├── http_get.py
│   │   ├── read_trace.py
│   │   └── run_scenario.py
│   ├── adapters/
│   │   ├── _base.sh           ← Shared contract utilities
│   │   ├── litellm.sh         ← LiteLLM adapter (primary)
│   │   ├── goose.sh           ← Goose agent adapter
│   │   └── mock.sh            ← Offline adapter
│   ├── mock-server/           ← Local OpenAI-compatible test server
│   ├── switch-model.sh        ← Provider switching
│   ├── health-check.sh        ← System health
│   └── start-colab-proxy.sh   ← Colab GPU setup
├── ollama-service/            ← Ollama container (tinyllama)
├── litellm-service/           ← LiteLLM router container
├── scenarios/                 ← Evaluation scenario specs
│   ├── agent-sim/
│   └── arb-agent-system/
├── skills/                    ← Agent Skills (Goose/Claude context)
│   ├── agent-sim/SKILL.md
│   ├── arb-agent-system/SKILL.md
│   ├── private-ai-stack/SKILL.md
│   └── ai-dev-platform/SKILL.md
├── Makefile                   ← Unified control surface
└── .env.example               ← Environment configuration template
```

---

## 🧠 LiteLLM Model Aliases

LiteLLM routes your task type to the right model automatically:

| Alias | Primary Model | Fallback | Best For |
|-------|--------------|----------|----------|
| `fast` | tinyllama (local) | — | Quick queries, always available |
| `general` | tinyllama (local) | — | Default, unclassified tasks |
| `code` | gpt-4.1 (OpenAI) | tinyllama | Code generation, debugging |
| `tooling` | gpt-4.1 (OpenAI) | tinyllama | Tool use, file operations |
| `claude` | claude-sonnet (Anthropic) | tinyllama | Complex reasoning |
| `smart` | gpt-4.1 → claude | tinyllama | Best available model |

The router classifies your task and sets `ACTIVE_MODEL` automatically:
```
"fix this bug"    → TASK_TYPE=code    → ACTIVE_MODEL=code    → gpt-4.1
"read this file"  → TASK_TYPE=tooling → ACTIVE_MODEL=tooling → gpt-4.1
"explain X"       → TASK_TYPE=general → ACTIVE_MODEL=fast    → tinyllama
```

---

## 🧪 Validation Ladder

```bash
make validate
```

Runs each layer independently — isolates failures precisely:

```
Step 1: mock adapter     → proves ./ai routes correctly
Step 2: mock server      → proves Goose/LiteLLM API call chain works
Step 3: ollama           → proves local LLM inference works
```

---

## 🏥 Health Check

```bash
make health
```

Checks:
- LiteLLM service reachability
- Ollama service + tinyllama model loaded
- Mock server readiness
- Goose CLI presence
- Active adapter and environment configuration
- Managed project endpoints

---

## 📊 Evaluation System

```bash
# Run a scenario
./ai run "validate agent-sim protocol"

# Evaluate the trace
./ai-eval .ai_trace.log scenarios/agent-sim/protocol_validation.json

# Output:
# ✅ PASS — Score: 0.95
#    Criteria: 3/3 met
```

Available scenarios:
- `scenarios/agent-sim/gridworld_basic.json`
- `scenarios/agent-sim/gridworld_chaos.json`
- `scenarios/agent-sim/protocol_validation.json`
- `scenarios/agent-sim/llm_vs_qlearning.json`
- `scenarios/arb-agent-system/spread_detection.json`
- `scenarios/arb-agent-system/health_check.json`

---

## 🔌 Adding Your Own Adapter

Implement the five standard commands:

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

Activate it:
```bash
chmod +x scripts/adapters/my-agent.sh
AI_ADAPTER=my-agent ./ai run "test"
```

**The interface is stable. Everything behind it is replaceable.**

---

## 🗺️ Roadmap

- [x] Stable `ai` CLI interface
- [x] Runtime v5.7 with structured trace logging
- [x] Router v3.2 with intent classification
- [x] LiteLLM integration (primary adapter)
- [x] Goose agent adapter
- [x] Mock offline adapter
- [x] Ollama local LLM service
- [x] Dev Container with unified Docker stack
- [x] Agent Skills for all managed projects
- [x] Evaluation CLI (`ai-eval`)
- [x] 7 evaluation scenarios
- [x] Python tool executor with plugin system
- [ ] Persistent sessions across container restarts
- [ ] Multi-project registry (`make register PROJECT=...`)
- [ ] Web UI control panel
- [ ] CI/CD integration guide
- [ ] Multi-user team configuration

---

## 🙏 Acknowledgments

- [LiteLLM](https://github.com/BerriAI/litellm) — Universal LLM router
- [Goose](https://block.github.io/goose/) — AI agent by Block
- [Ollama](https://ollama.ai/) — Local LLM runtime
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
