# 🧪 Mock OpenAI Server

A minimal OpenAI-compatible API server for deterministic local testing, protocol validation, and provider-isolation debugging.

---

# Purpose

The mock server validates the full:

```text id="jlwm4t"
runtime → adapter → HTTP API → response parsing
```

execution path without requiring:

* a real AI provider
* network connectivity
* GPU inference
* external credentials
* cloud APIs

Architecture flow:

```text id="hslw0h"
Dev Container
    └── Goose
            └── POST /v1/chat/completions
                        └── mock_openai.py
                                └── deterministic mock response
```

The mock server exists to isolate provider protocol behavior from runtime orchestration behavior.

---

# Mock Layers

The platform intentionally provides two distinct mock layers.

| Layer            | Purpose                                |
| ---------------- | -------------------------------------- |
| `mock.sh`        | deterministic adapter/runtime testing  |
| `mock_openai.py` | OpenAI-compatible API protocol testing |

These validate different failure boundaries.

---

## `mock.sh` Validates

* runtime orchestration
* adapter execution
* EventLedger integration
* lifecycle sequencing
* trace generation
* deterministic runtime behavior
* replay compatibility

Execution path:

```bash id="b4ys2f"
AI_ADAPTER=mock ./ai run "hello"
```

No network or HTTP stack is involved.

---

## `mock_openai.py` Validates

* OpenAI-compatible HTTP requests
* provider payload formatting
* request/response parsing
* client/server compatibility
* container networking
* provider protocol integration

Execution path:

```bash id="yoh9ib"
make mock-local
```

This validates the OpenAI protocol layer specifically.

---

# Deterministic Testing Philosophy

The mock server exists to provide:

* deterministic responses
* zero external dependencies
* replay-safe debugging
* protocol isolation
* provider-independent validation

This allows failures to be isolated cleanly between:

* runtime
* adapter
* protocol
* provider

The mock server is intentionally lightweight and deterministic.

---

# Relationship to Runtime Persistence

The mock OpenAI server operates above the runtime layer.

When used through:

```bash id="h2l5gf"
ai run ...
```

runtime persistence still occurs normally:

* `trace.jsonl`
* `ledger.jsonl`
* `run.json`
* `result.json`

This means mock-provider testing still validates:

* runtime lifecycle behavior
* replay compatibility
* EventLedger integration
* runtime orchestration
* append-only trace persistence

The mock server does not bypass runtime guarantees.

---

# Usage

## Start the Server

From project root:

```bash id="l6grxd"
make mock-server
```

Or manually:

```bash id="xgcg5i"
cd scripts/mock-server
uvicorn mock_openai:app --host 0.0.0.0 --port 8000
```

---

## Switch Runtime to Use Mock Server

```bash id="ny7x8r"
make mock-local
```

This configures the runtime to use the local OpenAI-compatible mock endpoint.

---

## Direct Validation

### Health Check

```bash id="9fg3dg"
curl http://localhost:8000/health
```

---

### List Models

```bash id="g9v8r9"
curl http://localhost:8000/v1/models
```

---

### Chat Completion

```bash id="wjlwm0"
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}]}'
```

---

# Runtime Validation Through AI CLI

```bash id="g4znwj"
ai run "hello from mock server"
```

Expected response:

```text id="7wjlwm"
[MOCK SERVER] Received: hello from mock server
```

This validates:

* runtime orchestration
* adapter behavior
* HTTP request formatting
* provider response parsing
* runtime persistence

---

# What This Validates

| Check                           | What It Proves                         |
| ------------------------------- | -------------------------------------- |
| server starts                   | FastAPI + uvicorn function correctly   |
| `/v1/models` responds           | provider discovery works               |
| `/v1/chat/completions` responds | OpenAI protocol formatting is correct  |
| response parsed correctly       | runtime/provider integration works     |
| `ai run` succeeds               | full runtime chain is operational      |
| traces generated                | runtime persistence remains functional |
| EventLedger emitted             | ledger integration remains operational |

---

# Non-Goals

The mock OpenAI server intentionally does NOT validate:

* model quality
* token streaming behavior
* GPU inference
* provider latency
* real tool execution
* production-scale concurrency
* provider rate limiting
* provider authentication edge cases
* production cost behavior

It validates protocol compatibility only.

---

# Debugging

The mock server echoes back the request context.

Example response:

```json id="0jlwm4"
{
  "choices": [{
    "message": {
      "content": "[MOCK SERVER] Received: your message\nDebug: {full request info}"
    }
  }]
}
```

This makes request debugging deterministic and replay-safe.

---

# Failure Isolation Workflow

If something fails with a real provider:

```bash id="zhx5b4"
make mock-local
ai run "test"
```

Interpretation:

| Result                       | Likely Problem          |
| ---------------------------- | ----------------------- |
| mock works                   | provider-specific issue |
| mock fails                   | runtime/platform issue  |
| HTTP calls fail              | protocol/config issue   |
| runtime persists incorrectly | runtime lifecycle issue |

---

# Failure Isolation Matrix

| Works               | Fails                 | Likely Problem             |
| ------------------- | --------------------- | -------------------------- |
| `mock.sh`           | `mock-local`          | OpenAI protocol layer      |
| `mock-local`        | `local`               | local model provider       |
| `local`             | `colab`               | remote networking/provider |
| `colab`             | `openai`              | provider auth/config       |
| runtime replay      | provider execution    | adapter/provider boundary  |
| runtime persistence | replay reconstruction | trace/ledger layer         |

This layered isolation model is intentional.

---

# Validation Ladder

```text id="k9m1h6"
make mock
    → mock.sh
    → validates runtime + adapter layer

make mock-local
    → mock_openai.py
    → validates OpenAI protocol layer

make local
    → Ollama
    → validates local inference provider

make colab
    → LiteLLM / remote GPU
    → validates remote provider integration

make openai
    → OpenAI cloud provider
    → validates production provider integration
```

Each layer introduces one additional operational dependency boundary.

Work upward incrementally.

---

# Operational Use Cases

Use the mock server when validating:

* provider request formatting
* OpenAI-compatible adapters
* runtime/provider integration
* container networking
* protocol debugging
* deterministic CI validation
* offline orchestration testing
* EventLedger/runtime persistence compatibility
* replay-safe provider isolation

---

# Streaming Support

The mock server currently returns deterministic non-streaming responses.

Streaming behavior is intentionally excluded to keep protocol validation:

* deterministic
* lightweight
* replay-safe
* CI-friendly

Streaming support may be added later as an additive compatibility feature.

---

# Runtime Compatibility Guarantees

The mock server preserves runtime guarantees:

* deterministic execution
* append-only persistence
* replay compatibility
* EventLedger compatibility
* schema-safe responses
* compatibility-safe runtime integration

The mock server is intentionally designed as:

```text id="jlwm4u"
deterministic provider protocol isolation infrastructure
```

—not merely a fake API endpoint.
