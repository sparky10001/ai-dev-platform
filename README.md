# 🤖 AI Dev Platform

> Stop managing AI tools. Start managing AI outcomes.

**A portable, provider-agnostic AI runtime and orchestration platform for developers building serious AI systems.**

One stable interface.
Any AI agent.
Any compute.
Anywhere.

---

# 🧠 Core Principle

> **Only one thing is stable: the AI interface.**
> Everything else can change, will change, should be replaceable.

```text
Developer
    │
    ▼
./ai run "your task"              ← Stable runtime CLI
./ai-orchestrate run "task"       ← Deterministic orchestration CLI
    │
    ▼
scripts/runtime.sh                ← Runtime entrypoint
    │
    ▼
runtime/engine.py                 ← Deterministic execution engine
    │
    ▼
control-plane/                    ← DAG orchestration layer
    │
    ▼
scripts/router.py                 ← Intent classification → model tier
    │
    ▼
scripts/adapters/agent.sh         ← Active adapter
    │
    ▼
scripts/agent.py                  ← LiteLLM tool-using agent
    │
    ▼
runtime/events.py                 ← Canonical NDJSON persistence
    │
    ▼
runtime/contracts.py              ← Schema compatibility guarantees
    │
    ▼
LiteLLM                            ← Universal provider router
    │
    ▼
Ollama │ OpenAI │ Claude │ NVIDIA NIM
```

Swap the adapter.
Swap the model.
Swap the compute.

**Your workflow never changes.**

---

# ✨ Features

- **Provider Agnostic** — LiteLLM routes to Ollama, OpenAI, Claude, NVIDIA NIM, or offline mock providers
- **Deterministic Runtime** — replay-safe NDJSON traces with schema-versioned contracts
- **Control-Plane DAG Orchestration** — additive orchestration layer with deterministic execution
- **Replay + Evaluation Engine** — reconstruct, score, compare, and export executions
- **Deterministic Policy Layer** — governance and execution constraints before DAG execution
- **Tool-Using Agent Runtime** — native OpenAI function-calling loop with dynamic tool execution
- **Dataset Export Layer** — deterministic NDJSON corpora generation
- **Schema Compatibility Contracts** — backward-compatible runtime guarantees
- **Scenario-Driven CI** — trace-based evaluation and scoring pipelines
- **Portable** — Docker-first architecture that works locally or in the cloud
- **Offline Mode** — mock adapter + mock OpenAI server support
- **Extensively Validated** — runtime + control-plane validation ladders

---

# 🚀 Quick Start

## Option 1 — Dev Container (Recommended)

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code:

```text
Reopen in Container
```

Then:

```bash
make health
make validate

./ai run "hello"
```

---

## Option 2 — Local Setup

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform

make setup
make litellm-fast

./ai run "hello"
```

---

# ⚡ Stable Runtime CLI

Everything flows through one stable runtime interface:

```bash
ai run      "analyze the runtime"
ai fix      "repair trace ordering"
ai explain  "how replay reconstruction works"
ai refactor "simplify the registry layer"
ai query    "what should I build next"
```

Examples:

```bash
./ai run "task" --trace
./ai run "task" --model=heavy
./ai --adapter=mock run "offline test"
```

---

# 🕹️ Control-Plane CLI

The control-plane CLI exposes deterministic orchestration behavior:

```bash
./ai-orchestrate plan "list files"

./ai-orchestrate run "list files"

./ai-orchestrate run \
  "Create a file called hello.txt with content 'hi' and then list files" \
  --trace
```

Supported commands:

```bash
./ai-orchestrate plan "task"
./ai-orchestrate run "task"
./ai-orchestrate validate-dag path/to/dag.json
./ai-orchestrate execute-dag path/to/dag.json
```

Policy-aware orchestration:

```bash
./ai-orchestrate run "list files" \
  --policy=safe-readonly
```

Features:

- deterministic planner
- deterministic policy validation
- validated DAG generation
- deterministic executor
- replayable DAG traces
- JSON-only command output
- isolated orchestration pipeline

The orchestration CLI is intentionally separate from the existing runtime CLI:

```text
./ai
  = runtime execution path

./ai-orchestrate
  = deterministic orchestration path
```

---

# 🧠 Model Tiers

| Tier | Purpose | Example |
|---|---|---|
| `fast` | low latency | tinyllama |
| `balanced` | reasoning | NVIDIA NIM |
| `heavy` | complex execution | GPT-4.1 / Claude |

Override manually:

```bash
./ai run "task" --model=heavy
```

---

# 🔄 Switching Providers

```bash
make litellm-fast
make litellm-balanced
make litellm-heavy

make mock
make mock-local

make colab
```

---

# 🧱 Deterministic Runtime Architecture

The runtime is built as a replay-safe,
schema-versioned execution system.

Core guarantees:

- deterministic NDJSON traces
- append-only persistence
- replay-safe lifecycle reconstruction
- crash-safe event durability
- schema-first validation
- backward compatibility

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
├── engine.py
├── events.py
├── replay.py
├── evals.py
├── registry.py
├── datasets.py
├── contracts.py
├── validator.py
├── loader.py
├── run.py
├── runner.py
└── schemas.py
```

---

# 🧩 Control-Plane Architecture

Stage 4 introduces an additive orchestration layer
built on top of the deterministic runtime.

The control-plane is intentionally separate from
the runtime execution substrate.

```text
Phase 3E runtime
    = execution + persistence substrate

Stage 4 control-plane
    = orchestration + DAG planning substrate
```

Control-plane components:

```text
control-plane/
├── cli/
├── core/
│   ├── dag/
│   │   ├── models.py
│   │   ├── validator.py
│   │   ├── executor.py
│   │   └── observability/
│   │       └── trace.py
│   ├── planner/
│   │   ├── planner.py
│   │   └── prompts.py
│   ├── policy/
│   │   ├── models.py
│   │   ├── defaults.py
│   │   └── validator.py
│   └── orchestrator/
│       └── orchestrator.py
├── tools/
│   ├── contracts.py
│   └── registry.py
├── dags/
│   ├── schemas/
│   └── examples/
└── tests/
```

---

# 🔄 Control-Plane Execution Flow

```text
task
  ↓
planner
  ↓
policy validation
  ↓
validated DAG
  ↓
tool registry validation
  ↓
deterministic executor
  ↓
runtime trace bridge
  ↓
Phase 3E replay/eval compatibility
```

The control-plane currently supports:

- deterministic DAG validation
- deterministic planner scaffolding
- deterministic policy/governance validation
- tool registry integration
- deterministic single-threaded DAG execution
- replayable DAG traces
- runtime-compatible execution artifacts
- orchestration request/result pipelines

---

# 🛡️ Policy Layer

Stage 4I introduces deterministic governance rules before execution.

Policies validate DAGs and orchestration requests before execution begins.

Current policy capabilities:

- tool allowlists
- tool denylists
- max DAG node limits
- dependency fanout limits
- LLM node restrictions
- workspace path boundaries
- traversal protection

Example:

```text
planner
→ policy validation
→ executor
```

Included policies:

| Policy | Purpose |
|---|---|
| `default` | permissive deterministic policy |
| `safe-readonly` | read-only orchestration policy |

Example:

```bash
./ai-orchestrate run "list files" \
  --policy=safe-readonly
```

---

# 🧠 Runtime Philosophy

The runtime is treated as:

```text
deterministic infrastructure
```

—not merely an agent wrapper.

This enables:

- replayable executions
- reproducible debugging
- trace-driven evaluation
- deterministic dataset generation
- execution introspection
- contract-safe evolution

All runtime artifacts are schema-versioned and replay-safe by default.

---

# 🌍 Environment Scenarios

## 🏠 Local AI

```bash
make litellm-fast
./ai run "review the convergence issue"
```

---

## ☁️ Cloud Intelligence

```bash
make litellm-heavy
./ai run "refactor the runtime engine"
```

---

## ✈️ Offline Mode

```bash
make mock
./ai run "plan next sprint"
```

---

## 🖥️ GPU Compute

```bash
make colab
./ai run "train policy agent"
```

---

# 📁 Project Structure

```text
ai-dev-platform/
├── ai
├── ai-orchestrate
├── ai-eval
├── runtime/
├── control-plane/
│   ├── cli/
│   ├── core/
│   │   ├── dag/
│   │   ├── planner/
│   │   ├── policy/
│   │   ├── orchestrator/
│   │   └── observability/
│   ├── tools/
│   ├── dags/
│   └── tests/
├── scripts/
├── scenarios/
├── runs/
├── evals/
├── docs/
├── skills/
├── Makefile
└── .env.example
```

---

# 🧰 Tool System

The platform supports runtime-discovered tools.

| Tool | Purpose |
|---|---|
| `read_file` | read workspace files |
| `write_file` | write files safely |
| `list_files` | enumerate directories |
| `run_bash` | execute shell commands |
| `http_get` | HTTP GET requests |
| `read_trace` | replay trace inspection |
| `run_scenario` | scenario execution |
| `evaluate_trace` | runtime evaluation |
| `compare_results` | compare evaluation runs |

Tools are exported automatically as OpenAI-compatible function schemas.

---

# 🧪 Scenario-Driven Evaluation

Run structured evaluations:

```bash
./scripts/run_scenario.sh \
  scenarios/tests/test_list_files_v2.json \
  --model=balanced
```

Example:

```text
🔍 Tools called: write_file, list_files
🎯 SCORE: 1
✅ Scenario passed
```

---

# 🧪 Runtime Validation Ladder

Phase 3E runtime validation:

```bash
make validate
```

Core runtime suites:

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

# 🧪 Control-Plane Validation Ladder

Stage 4 additive validation:

```bash
make control-plane-tests
```

Control-plane suites:

```bash
make control-plane-dag-tests
make control-plane-tool-tests
make control-plane-executor-tests
make control-plane-trace-tests
make control-plane-planner-tests
make control-plane-orchestrator-tests
make control-plane-cli-tests
make control-plane-policy-tests
```

Important:

```text
Stage 4 tests are additive and intentionally
NOT part of make validate yet.
```

This keeps the deterministic runtime substrate stable while the orchestration layer evolves independently.

---

# 🔌 Adding Your Own Adapter

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

# 🗺️ Roadmap

## Phase 3E Runtime

- [x] Stable CLI
- [x] Deterministic runtime architecture
- [x] Replay-safe NDJSON persistence
- [x] Runtime replay engine
- [x] Runtime evaluation engine
- [x] Registry/query layer
- [x] Dataset export pipelines
- [x] Schema compatibility contracts
- [x] Runtime validation ladder

## Stage 4 Control-Plane

- [x] DAG schema + validator
- [x] Tool registry bridge
- [x] Deterministic DAG executor
- [x] Replayable DAG traces
- [x] Control-plane validation ladder
- [x] Deterministic DAG planner
- [x] Planner/executor orchestration pipeline
- [x] Control-plane CLI
- [x] Planner policy layer
- [ ] Parallel DAG execution
- [ ] Orchestration API
- [ ] Web UI
- [ ] LLM-assisted planner

## Platform

- [x] LiteLLM routing
- [x] Native tool-calling agent loop
- [x] Scenario-driven evaluation
- [x] Unified Docker stack
- [x] Offline mock adapter
- [ ] Persistent sessions
- [ ] Multi-project registry
- [ ] CI/CD integration guide

---

# 🙏 Acknowledgments

- LiteLLM
- Ollama
- Goose
- NVIDIA NIM
- OpenAI
- Anthropic
- agent-sim
- private-ai-stack

---

# 📄 License

MIT License — see `LICENSE`.

---

<p align="center">
Built with ❤️ by James R. Glines<br>
The interface is stable. Everything else is replaceable.
</p>