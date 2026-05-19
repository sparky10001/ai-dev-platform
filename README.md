# 🤖 AI Dev Platform

> Stop managing AI tools. Start managing AI outcomes.

**A portable, provider-agnostic AI runtime and orchestration platform for developers building deterministic, replay-safe AI systems.**

One stable interface.
Any AI agent.
Any compute.
Anywhere.

Now with:

* deterministic orchestration experimentation
* replay-safe evaluation
* adaptive strategy benchmarking
* orchestration lineage reconstruction
* graph analytics
* bounded parallel DAG execution
* additive EventLedger compatibility
* operational ledger health auditing

---

# 🧠 Core Principle

> **Only one thing is stable: the AI interface.**
> Everything else can change, will change, and should be replaceable.

---

# Architecture Status

The platform currently operates in:

* deterministic single-host mode
* append-only NDJSON persistence
* replay-safe execution mode
* additive EventLedger compatibility mode

Current defaults:

* `trace.jsonl` remains canonical
* `ledger.jsonl` operates in additive compatibility mode
* orchestration remains deterministic and local-first
* no autonomous planning is enabled by default

---

# What This Is NOT

This platform is intentionally NOT:

* a black-box autonomous agent framework
* a prompt-chain orchestration toy
* a vector-database memory system
* an agent swarm platform
* an opaque AI abstraction layer

It IS:

* deterministic infrastructure
* replay-safe orchestration
* schema-versioned runtime execution
* provider-agnostic runtime tooling
* additive orchestration experimentation

---

# 🧱 Current Runtime Architecture

```text id="vkbw8r"
Developer
    │
    ▼
Stable CLI
    │
    ▼
Runtime Engine
    │
    ▼
Event Persistence
    ├── trace.jsonl   (canonical)
    └── ledger.jsonl  (additive compatibility)
    │
    ▼
Replay / Eval / Registry / Datasets
    │
    ▼
Control-Plane Orchestration
```

---

# ⚡ Stable Runtime Interface

Everything flows through one stable runtime interface:

```bash id="lhf8v2"
./ai run "your task"
./ai fix "repair runtime issue"
./ai explain "describe replay behavior"
./ai refactor "simplify orchestration"
./ai query "what should I build next"
```

Examples:

```bash id="8tmjpb"
./ai run "analyze the runtime" --trace

./ai run "refactor the replay layer" \
  --model=heavy

./ai --adapter=mock run "offline validation"
```

---

# 🧠 Runtime Philosophy

The runtime is treated as:

```text id="y1r0y0"
deterministic infrastructure
```

—not merely an agent wrapper.

This enables:

* replayable executions
* deterministic debugging
* trace-driven evaluation
* schema-safe evolution
* orchestration experimentation
* historical orchestration reconstruction
* replay-backed analytics
* deterministic parallel orchestration

---

# ✨ Core Features

## Runtime

* Provider-agnostic execution
* Deterministic NDJSON persistence
* Replay-safe lifecycle reconstruction
* Schema-versioned contracts
* Dataset export pipelines
* Runtime replay + evaluation engine
* Registry/query layer
* Offline mock support
* EventLedger compatibility layer

---

## Control-Plane Orchestration

* Deterministic DAG orchestration
* Policy-aware execution
* Replay-safe orchestration traces
* Scenario-driven orchestration testing
* Strategy experimentation
* Benchmark suites
* Adaptive orchestration heuristics
* Orchestration memory + recall
* Knowledge graph lineage reconstruction
* Graph analytics
* Bounded deterministic parallel DAG execution

---

## Operational Observability

Built-in operational audit tooling includes:

* ledger drift detection
* ledger corruption validation
* parity enforcement
* runtime boundary auditing
* derived-system purity auditing
* trace compatibility auditing
* ledger health reporting
* dry-run ledger readiness evaluation

All observability tooling is:

* deterministic
* read-only
* additive
* replay-safe

---

# 🛡️ Stability Guarantees

The platform guarantees:

* append-only runtime persistence
* deterministic replay reconstruction
* schema-versioned compatibility
* replay-safe orchestration
* deterministic event ordering
* bounded parallel execution
* additive migration behavior
* trace/ledger parity validation

---

# 🚀 Quick Start

## Option 1 — Dev Container (Recommended)

```bash id="uqs0fg"
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code:

```text id="l6cwgs"
Reopen in Container
```

Then:

```bash id="wpg49n"
make health
make validate

./ai run "hello"
```

---

## Option 2 — Local Setup

```bash id="3phq6y"
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform

make setup
make litellm-fast

./ai run "hello"
```

---

# 🕹️ Control-Plane CLI

The control-plane exposes deterministic orchestration behavior:

```bash id="e7l0t5"
./ai-orchestrate plan "list files"

./ai-orchestrate run "list files"

./ai-orchestrate run \
  "Create a file called tmp/hello.txt with content 'hi' and then list files" \
  --trace
```

Supported execution:

```bash id="t7a2o7"
./ai-orchestrate execute-dag path/to/dag.json

./ai-orchestrate execute-dag path/to/dag.json \
  --parallel \
  --max-workers=4
```

Policy-aware orchestration:

```bash id="q4lqso"
./ai-orchestrate run "list files" \
  --policy=safe-readonly
```

The orchestration layer is intentionally separate:

```text id="hixjsv"
./ai
  = runtime execution substrate

./ai-orchestrate
  = orchestration substrate
```

---

# 🧩 Runtime Architecture

Core runtime modules:

```text id="lkk96k"
runtime/
├── engine.py
├── trace_pipeline.py
├── event_ledger.py
├── replay.py
├── evals.py
├── registry.py
├── datasets.py
├── contracts.py
├── validator.py
├── loader.py
├── run.py
├── schemas.py
└── audits/
```

Core guarantees:

* append-only persistence
* deterministic ordering
* replay-safe reconstruction
* schema-first validation
* compatibility-safe evolution

Runtime lifecycle:

```text id="4mvjgx"
session_start
→ tool_call
→ tool_result
→ agent_output
→ session_end
```

---

# 🔄 EventLedger Migration

The platform currently operates in additive EventLedger compatibility mode.

Current behavior:

* `trace.jsonl` remains canonical by default
* `ledger.jsonl` mirrors validated runtime events
* replay/eval/registry support dual-source operation
* parity/drift/corruption audits validate cutover readiness

The migration remains:

* additive
* replay-safe
* rollback-safe
* non-destructive

No authority switch occurs unless explicitly enabled.

Controlled canary mode for ledger-authoritative validation is available via:

- `make ledger-canary`
- `make ledger-canary-summary`

See:
- `docs/maintenance.md`

---

# 🧪 Runtime Validation

Core runtime validation:

```bash id="9vt3mj"
make validate
```

Core runtime suites include:

```bash id="ajywyw"
./scripts/tests/runtime_tests.sh
./scripts/tests/failure_tests.sh
./scripts/tests/replayability_smoke_test.sh
./scripts/tests/runtime_eval_tests.sh
./scripts/tests/runtime_registry_tests.sh
./scripts/tests/runtime_dataset_tests.sh
./scripts/tests/runtime_contract_tests.sh
./scripts/tests/runtime_event_ledger_tests.sh
./scripts/tests/runtime_ledger_health_tests.sh
./scripts/tests/runtime_trace_compatibility_tests.sh
```

---

# 🧪 Control-Plane Validation

Control-plane validation remains additive:

```bash id="p5d3rl"
make control-plane-tests
```

Major suites:

```bash id="ql9mwr"
make control-plane-dag-tests
make control-plane-orchestrator-tests
make control-plane-policy-tests
make control-plane-scenario-tests
make control-plane-replay-tests
make control-plane-eval-tests
make control-plane-benchmark-tests
make control-plane-parallel-tests
```

Stage 4 validation remains intentionally isolated from the core runtime validation ladder.

---

# 🔄 Switching Providers

```bash id="f7bgp1"
make litellm-fast
make litellm-balanced
make litellm-heavy

make mock
make mock-local

make colab
```

Supported providers:

* Ollama
* OpenAI
* Claude
* NVIDIA NIM
* Offline mock adapters

---

# 🧪 Scenario-Driven Evaluation

Run structured deterministic evaluations:

```bash id="9jjlwm"
AI_ADAPTER=mock \
./scripts/runtime_run_scenario.sh \
  scenarios/tests/test_list_files_v3.json \
  --model=balanced
```

Optional timeout:

```bash id="h3k5sq"
AI_ADAPTER=mock \
SCENARIO_TIMEOUT=60 \
./scripts/runtime_run_scenario.sh \
  scenarios/tests/test_list_files_v3.json \
  --model=fast
```

---

# 🧠 Model Tiers

| Tier       | Purpose           | Example          |
| ---------- | ----------------- | ---------------- |
| `fast`     | low latency       | tinyllama        |
| `balanced` | reasoning         | NVIDIA NIM       |
| `heavy`    | complex execution | GPT-4.1 / Claude |

Override manually:

```bash id="8rj6di"
./ai run "task" --model=heavy
```

---

# 🌍 Environment Modes

## 🏠 Local AI

```bash id="c63lki"
make litellm-fast
./ai run "review the replay issue"
```

---

## ☁️ Cloud Intelligence

```bash id="qj8o5t"
make litellm-heavy
./ai run "refactor orchestration planner"
```

---

## ✈️ Offline Mode

```bash id="4bn5m7"
make mock
./ai run "plan next sprint"
```

---

## 🖥️ GPU Compute

```bash id="6jlwmu"
make colab
./ai run "train orchestration heuristics"
```

---

# 🧰 Runtime Tool System

The platform supports runtime-discovered tools.

| Tool              | Purpose                |
| ----------------- | ---------------------- |
| `read_file`       | read workspace files   |
| `write_file`      | write files safely     |
| `list_files`      | enumerate directories  |
| `run_bash`        | execute shell commands |
| `http_get`        | HTTP requests          |
| `read_trace`      | replay inspection      |
| `run_scenario`    | scenario execution     |
| `evaluate_trace`  | runtime evaluation     |
| `compare_results` | replay comparison      |

Tools export automatically as OpenAI-compatible function schemas.

---

# 📁 Project Structure

```text id="jjlwmv"
ai-dev-platform/
├── ai
├── ai-orchestrate
├── runtime/
├── control-plane/
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

# 🧠 Production Philosophy

The platform prioritizes:

1. deterministic execution
2. replay-safe debugging
3. additive evolution
4. schema-versioned compatibility
5. operational observability
6. provider independence
7. infrastructure-first design

---

# 🗺️ Roadmap

## Runtime

* [x] Stable CLI
* [x] Deterministic runtime architecture
* [x] Replay-safe NDJSON persistence
* [x] Runtime replay engine
* [x] Runtime evaluation engine
* [x] Registry/query layer
* [x] Dataset export pipelines
* [x] EventLedger compatibility layer
* [x] Runtime observability audits
* [ ] Persistent sessions
* [ ] Multi-project registry

---

## Control-Plane

* [x] Deterministic DAG executor
* [x] Policy validation
* [x] Replay/introspection
* [x] Benchmark suites
* [x] Multi-strategy experimentation
* [x] Orchestration memory
* [x] Knowledge graph lineage
* [x] Graph analytics
* [x] Parallel DAG execution
* [ ] Orchestration API
* [ ] Distributed orchestration execution
* [ ] Web UI
* [ ] LLM-assisted planner

---

## Platform

* [x] LiteLLM routing
* [x] Scenario-driven evaluation
* [x] Unified Docker stack
* [x] Offline mock adapters
* [ ] CI/CD integration guide

---

# 🙏 Acknowledgments

* LiteLLM
* Ollama
* Goose
* NVIDIA NIM
* OpenAI
* Anthropic
* agent-sim
* private-ai-stack

---

# 📄 License

MIT License — see `LICENSE`.

---

<p align="center">
Built with ❤️ by James R. Glines<br>
The interface is stable. Everything else is replaceable.
</p>
