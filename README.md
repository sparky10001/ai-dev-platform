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
LiteLLM                           ← Universal provider router
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
- **Control-Plane Scenario Testing** — deterministic orchestration scenario validation
- **Replay + Introspection Layer** — deterministic orchestration reconstruction, lineage, and export tooling
- **Evaluation + Comparison Layer** — deterministic orchestration scoring, benchmarking, and replay comparison
- **Experiment Tracking + Datasets** — deterministic replay-backed experiment manifests, datasets, and benchmark corpora
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

The runtime is built as a replay-safe, schema-versioned execution system.

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

Stage 4 introduces an additive orchestration layer built on top of the deterministic runtime.

The control-plane is intentionally separate from the runtime execution substrate.

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
│   ├── orchestrator/
│   │   └── orchestrator.py
│   ├── scenarios/
│   │   ├── models.py
│   │   ├── runner.py
│   │   └── evaluator.py
│   ├── replay/
│   │   ├── models.py
│   │   ├── loader.py
│   │   ├── introspection.py
│   │   └── exporter.py
│   ├── evals/
│   │   ├── models.py
│   │   ├── evaluator.py
│   │   ├── comparator.py
│   │   ├── benchmarks.py
│   │   └── exporter.py
│   └── experiments/
│       ├── models.py
│       ├── manifests.py
│       ├── tracker.py
│       ├── datasets.py
│       └── exporter.py
├── tools/
│   ├── contracts.py
│   └── registry.py
├── dags/
│   ├── schemas/
│   └── examples/
├── scenarios/
│   ├── tests/
│   └── README.md
└── tests/
```

---

# 🔄 Control-Plane Execution Flow

```
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
replay/eval-compatible artifacts
  ↓
scenario evaluation
  ↓
replay + introspection
  ↓
evaluation + comparison
  ↓
experiment tracking + datasets
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
- orchestration replay reconstruction
- orchestration lineage + export tooling
- orchestration scenario validation
- orchestration replay comparison
- orchestration benchmarking
- deterministic orchestration scoring
- orchestration experiment manifests
- replay-backed dataset generation
- orchestration benchmark corpora
- deterministic experiment exports

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

Execution flow:

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

# 🧪 Control-Plane Scenario Testing

Stage 4J introduces deterministic orchestration scenario validation.

Control-plane scenarios validate the complete orchestration path:

```text
task
→ planner
→ policy validation
→ executor
→ optional trace
→ replay/eval-compatible result
```

Scenarios are JSON-defined and replay-safe.

Scenario capabilities:

- orchestration result validation
- DAG validation
- policy violation validation
- trace artifact validation
- replay compatibility checks
- deterministic scoring
- end-to-end orchestration evaluation

Scenario files live in:

```text
control-plane/scenarios/tests/
```

Example:

```bash
python3 -m control-plane.core.scenarios.runner \
  control-plane/scenarios/tests/write_then_list.json
```

Example scenario categories:

| Scenario | Purpose |
|---|---|
| `list_files.json` | deterministic read workflow |
| `write_then_list.json` | multi-node orchestration |
| `safe_readonly_blocks_write.json` | policy enforcement |
| `traced_write_then_list.json` | replayable orchestration |
| `unsupported_task_noop.json` | noop fallback behavior |

Scenario tests are included in:

```bash
make control-plane-tests
```

# 🔍 Replay + Introspection Layer

Stage 4K introduces deterministic orchestration replay and introspection.

Replay reconstructs orchestration DAG executions directly from replay-safe traces.

Replay capabilities:

- orchestration reconstruction
- DAG replay summaries
- execution lineage graphs
- execution ordering reconstruction
- failed/skipped node analysis
- replay-safe orchestration exports
- deterministic orchestration introspection

Replay reconstruction flow:

```text
trace.jsonl
→ orchestration replay loader
→ DAG reconstruction
→ introspection helpers
→ export/report generation
```

Replay CLI commands:

```bash
./ai-orchestrate replay runs/<run_id>

./ai-orchestrate summarize-run runs/<run_id>

./ai-orchestrate export-run runs/<run_id> report.md

./ai-orchestrate export-run runs/<run_id> report.json
```

Replay exports support:

- JSON summaries
- Markdown orchestration reports
- deterministic lineage reconstruction
- replay-safe orchestration inspection

Replay validation is included in:

```bash
make control-plane-tests
```

# 📊 Evaluation + Comparison Layer

Stage 4L introduces deterministic orchestration evaluation, benchmarking, and replay comparison.

The evaluation layer operates entirely on replay-safe orchestration artifacts.

Evaluation capabilities:

- orchestration scoring
- replay comparison
- DAG diffing
- orchestration benchmarking
- execution quality analysis
- execution completeness metrics
- replay-safe benchmark exports

Evaluation flow:

```text
ReplayDag
→ evaluation engine
→ comparison engine
→ benchmark aggregation
→ deterministic exports
```

Supported evaluation CLI commands:

```bash
./ai-orchestrate evaluate-run runs/<run_id>

./ai-orchestrate compare-runs runs/<run_a> runs/<run_b>

./ai-orchestrate benchmark-runs runs/a runs/b runs/c
```

Evaluation features:

- deterministic orchestration scoring
- replay-safe comparison
- execution-order diffing
- tool usage comparison
- benchmark aggregation
- markdown benchmark exports
- JSON evaluation exports

Evaluation validation is included in:

```bash
make control-plane-tests
```

# 🧪 Experiment Tracking + Datasets

Stage 4M introduces deterministic orchestration experiment tracking and replay-backed dataset generation.

The experiment layer operates entirely on replay-safe orchestration artifacts.

Experiment capabilities:

- orchestration experiment manifests
- replay dataset generation
- benchmark corpora construction
- orchestration lineage metadata
- evaluation history aggregation
- deterministic experiment exports
- replay-safe dataset construction

Experiment flow:

```text
ReplayDag
→ evaluation
→ experiment tracker
→ dataset builder
→ manifest aggregation
→ deterministic exports
```

Supported experiment CLI commands:

```bash
./ai-orchestrate track-run runs/<run_id>

./ai-orchestrate track-experiment runs/a runs/b runs/c

./ai-orchestrate build-dataset runs/a runs/b runs/c

./ai-orchestrate export-experiment runs/a runs/b report.md
```

Experiment features:

- deterministic experiment manifests
- replay-backed datasets
- benchmark corpus generation
- evaluation lineage tracking
- markdown experiment exports
- JSON dataset exports

Experiment validation is included in:

```bash
make control-plane-tests
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
├── control-plane/
│   ├── cli/
│   ├── core/
│   │   ├── dag/
│   │   ├── planner/
│   │   ├── policy/
│   │   ├── orchestrator/
│   │   ├── observability/
│   │   ├── scenarios/
│   │   ├── replay/
│   │   └── evals/
│   ├── tools/
│   ├── dags/
│   ├── scenarios/
│   └── tests/
├── scripts/
│   ├── runtime.sh
│   ├── router.py
│   ├── agent.py
│   ├── tool_executor.py
│   ├── adapters/
│   ├── tools/
│   ├── tests/
│   └── mock-server/
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
make control-plane-scenario-tests
make control-plane-replay-tests
make control-plane-eval-tests
make control-plane-experiment-tests
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
- [x] Control-plane scenario testing
- [x] Orchestration replay/introspection
- [x] Orchestration evaluation/comparison
- [x] Orchestration datasets/experiment tracking
- [ ] Policy/planner benchmark suites
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
