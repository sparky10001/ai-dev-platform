````markdown
# 🤖 AI Dev Platform

> Stop managing AI tools. Start managing AI outcomes.

**A portable, provider-agnostic AI development environment for developers who build serious things.**

One stable interface. Any AI agent. Any compute. Anywhere.

---

## 🧠 Core Principle

> **Only one thing is stable: the AI interface.**
> Everything else can change, will change, should be replaceable.

```text
Developer
    │
    ▼
./ai run "your task"          ← Stable CLI — never changes
    │
    ▼
scripts/runtime.sh            ← Runtime entrypoint
    │
    ▼
runtime/engine.py             ← Deterministic execution engine
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
runtime/events.py             ← Canonical NDJSON event persistence
    │
    ▼
runtime/contracts.py          ← Schema compatibility guarantees
    │
    ▼
LiteLLM (http://litellm:4000) ← Universal router
    │
    ▼
Ollama │ OpenAI │ Claude │ NVIDIA NIM   ← Replaceable compute
````

Swap the adapter. Swap the model. Swap the compute.
**Your workflow never changes.**

---

## ✨ Features

* **Provider Agnostic** — LiteLLM routes to Ollama, OpenAI, Anthropic/Claude, NVIDIA NIM, or fully offline mock
* **Intent-Based Routing** — command type maps automatically to the right model tier (fast / balanced / heavy)
* **Tool-Using Agent** — native OpenAI function-calling loop with built-in tools
* **Deterministic Runtime** — schema-versioned NDJSON traces with replay-safe lifecycle persistence
* **Replay + Evaluation Engine** — reconstruct runs, score outcomes, compare executions
* **Dataset Export Layer** — export traces/evals as deterministic NDJSON corpora
* **Contract-Stabilized Architecture** — backward-compatible runtime schemas with validation guarantees
* **Simulation-Driven CI** — scenario specs, trace evaluation, and automated scoring
* **Portable** — unified Docker stack, works on any machine or on a plane
* **Project Aware** — inject context for agent-sim, arb-agent-system, private-ai-stack
* **Extensively Validated** — runtime validation ladder covering replay, contracts, datasets, evals, isolation, NDJSON integrity, and lifecycle ordering
* **Offline Mode** — mock adapter works without internet

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
make status
make health
./ai run "hello"
```

---

### Option 2 — Local Setup

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform

make setup
make litellm-fast

./ai run "hello"
```

---

## 📋 Requirements

| Tool               | Required      | Notes                    |
| ------------------ | ------------- | ------------------------ |
| Docker             | ✅ Yes         | Unified dev stack        |
| VS Code            | ✅ Recommended | Dev Containers extension |
| OpenAI API Key     | Optional      | GPT models               |
| Anthropic API Key  | Optional      | Claude models            |
| NVIDIA NIM API Key | Optional      | Free reasoning models    |
| Goose CLI          | Optional      | Goose adapter support    |

---

## ⚡ The `ai` Command

Everything flows through one stable interface:

```bash
ai run      "analyze the protocol layer"
ai fix      "ImportError in runtime engine"
ai explain  "how replay reconstruction works"
ai refactor "simplify the dataset exporter"
ai query    "what should I build next"
```

Flags:

```bash
./ai run "task" --trace
./ai run "task" --model=heavy
./ai --adapter=mock run "task"
```

---

## 🧠 Model Tiers

Commands map automatically to model tiers.

| Tier       | Command                  | Primary          | Fallback  | Use When        |
| ---------- | ------------------------ | ---------------- | --------- | --------------- |
| `fast`     | `query`                  | tinyllama        | —         | quick responses |
| `balanced` | `explain`                | NVIDIA NIM       | tinyllama | reasoning       |
| `heavy`    | `run`, `fix`, `refactor` | GPT-4.1 / Claude | tinyllama | complex tasks   |

Override manually:

```bash
./ai run "task" --model=fast
./ai run "task" --model=heavy
ACTIVE_MODEL=balanced ./ai run "task"
```

---

## 🔄 Switching Providers

```bash
make litellm-fast
make litellm-balanced
make litellm-code
make litellm-claude
make litellm-heavy

make mock
make mock-local

make colab
```

---

## 🧱 Deterministic Runtime Architecture

The runtime is built as a replay-safe,
schema-versioned execution system.

Core guarantees:

* deterministic NDJSON traces
* append-only persistence
* replay-safe lifecycle reconstruction
* backward-compatible contracts
* schema-first validation
* crash-safe event durability

Runtime lifecycle:

```text
session_start
→ tool_call
→ tool_result
→ agent_output
→ session_end
```

Core runtime modules:

```text
runtime/
├── engine.py       ← orchestration engine
├── events.py       ← canonical event writer
├── replay.py       ← deterministic replay loader
├── evals.py        ← execution scoring + comparisons
├── registry.py     ← run indexing/query layer
├── datasets.py     ← NDJSON export pipelines
├── contracts.py    ← schema compatibility guarantees
├── validator.py    ← validation boundary
├── loader.py       ← runtime artifact loading
├── run.py          ← canonical run management
├── runner.py       ← adapter execution layer
└── schemas.py      ← typed runtime models
```

---

## 🧠 Runtime Philosophy

The runtime is treated as deterministic infrastructure,
not merely an agent wrapper.

This enables:

* replayable executions
* trace-driven evaluation
* reproducible debugging
* dataset generation
* contract-safe evolution
* execution introspection

All runtime artifacts are schema-versioned and replay-safe by default.

---

## 🌍 Environment Scenarios

### 🏠 Private Local AI

```bash
make litellm-fast
./ai run "review the convergence issue"
```

### ☁️ Cloud Intelligence

```bash
make litellm-heavy
./ai run "refactor the risk service"
```

### ✈️ Offline

```bash
make mock
./ai run "plan the next sprint"
```

### 🖥️ GPU Compute

```bash
make colab
./ai run "train Q-agent for 10000 episodes"
```

---

## 📁 Project Structure

```text
ai-dev-platform/
├── ai
├── ai-eval
├── runtime/
│   ├── engine.py
│   ├── events.py
│   ├── replay.py
│   ├── evals.py
│   ├── registry.py
│   ├── datasets.py
│   ├── contracts.py
│   ├── validator.py
│   ├── loader.py
│   ├── run.py
│   ├── runner.py
│   └── schemas.py
├── scripts/
│   ├── runtime.sh
│   ├── router.py
│   ├── agent.py
│   ├── tool_executor.py
│   ├── run_scenario.sh
│   ├── health-check.sh
│   ├── switch-model.sh
│   ├── adapters/
│   ├── tools/
│   ├── mock-server/
│   └── tests/
├── scenarios/
├── evals/
├── runs/
├── docs/
├── skills/
├── Makefile
└── .env.example
```

---

## 🧰 Tool System

The agent supports runtime-discovered tools.

| Tool              | Description             |
| ----------------- | ----------------------- |
| `read_file`       | Read workspace files    |
| `write_file`      | Write files safely      |
| `list_files`      | Enumerate directories   |
| `run_bash`        | Execute shell commands  |
| `http_get`        | HTTP GET requests       |
| `read_trace`      | Parse runtime traces    |
| `run_scenario`    | Execute scenario specs  |
| `evaluate_trace`  | Score runtime traces    |
| `compare_results` | Compare evaluation runs |

Tools are exported automatically as OpenAI-compatible function schemas.

---

## 🧪 Scenario-Driven Evaluation

Run tasks against structured success criteria:

```bash
./scripts/run_scenario.sh \
  scenarios/tests/test_list_files_v2.json \
  --model=balanced
```

Example output:

```text
🔍 Tools called: write_file, list_files
🎯 SCORE: 1
✅ Scenario passed
```

Scenario format:

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

Supported criteria:

* `tool_used`
* `no_errors`
* `output_contains`

---

## 🧪 Runtime Validation Ladder

The runtime includes deterministic validation suites for:

* runtime contracts
* replay compatibility
* NDJSON integrity
* lifecycle ordering
* crash recovery
* parallel isolation
* dataset exports
* evaluation pipelines
* registry/query correctness
* backward compatibility

Run full validation:

```bash
make validate
```

Core suites:

```bash
./scripts/tests/runtime_tests.sh
./scripts/tests/failure_tests.sh
./scripts/tests/replayability_smoke_test.sh
./scripts/tests/runtime_eval_tests.sh
./scripts/tests/runtime_registry_tests.sh
./scripts/tests/runtime_dataset_tests.sh
./scripts/tests/runtime_contract_tests.sh
./scripts/tests/test_adapters.sh
./scripts/tests/tool_test_v2.sh
```

---

## 🔌 Adding Your Own Adapter

```bash
#!/bin/bash

ADAPTER_NAME="my-agent"

source "$(dirname "$0")/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

case "$COMMAND" in
  run)
    RESPONSE=$(my_agent "$INPUT")
    ;;
  *)
    build_response "error" "Unknown command"
    adapter_exit
    ;;
esac

build_response "done" "$RESPONSE"
adapter_exit
```

Enable:

```bash
chmod +x scripts/adapters/my-agent.sh
AI_ADAPTER=my-agent ./ai run "test"
```

---

## 🗺️ Roadmap

* [x] Stable `ai` CLI
* [x] Deterministic runtime architecture
* [x] Replay-safe NDJSON persistence
* [x] Runtime evaluation engine
* [x] Runtime registry/query layer
* [x] Dataset export pipelines
* [x] Schema compatibility contracts
* [x] Runtime validation ladder
* [x] LiteLLM tier routing
* [x] Native tool-calling agent loop
* [x] Scenario-driven evaluation
* [x] Unified Docker stack
* [x] Mock offline adapter
* [ ] Persistent sessions
* [ ] Multi-project registry
* [ ] Web UI
* [ ] CI/CD integration guide
* [ ] Direct NVIDIA NIM adapter

---

## 🙏 Acknowledgments

* LiteLLM
* Ollama
* Goose
* NVIDIA NIM
* OpenAI
* Anthropic
* agent-sim
* private-ai-stack

---

## 📄 License

MIT License — see `LICENSE`.

---

<p align="center">
Built with ❤️ by James R. Glines<br>
The interface is stable. Everything else is replaceable.
</p>
```
