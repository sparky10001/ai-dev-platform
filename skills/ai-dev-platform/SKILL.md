---
name: ai-dev-platform
description: >
  Use this skill when working on ai-dev-platform — a portable, provider-agnostic
  AI development environment that manages agent-sim, arb-agent-system, and
  private-ai-stack through a stable unified interface. Activate when the user
  mentions ai-dev-platform, adapter switching, Goose configuration, mock server,
  provider switching, validation ladder, or the ai script.
---

# ai-dev-platform

> "Only one thing is stable: the AI interface.
> Everything else can change, will change, should be replaceable."

## Project Overview

ai-dev-platform is a portable, provider-agnostic AI development environment
for developers who manage multiple AI-assisted projects. One stable interface.
Any AI agent. Any compute. Anywhere — at home, at work, on a plane.

## Core Architecture

```
Developer
    │
    ▼
./scripts/ai run "your task"     ← STABLE — never changes
    │
    ▼
scripts/adapters/ai.sh           ← Symlink to active adapter
    │
    ▼
goose.sh │ mock.sh │ http-agent.sh   ← Swappable adapters
    │
    ▼
OpenAI │ Colab │ Local Ollama │ Mock   ← Replaceable providers
```

## Project Structure

```
ai-dev-platform/
├── .devcontainer/
│   ├── devcontainer.json    ← VS Code Dev Container config
│   ├── Dockerfile           ← Ubuntu 22.04 + Python + Node + Goose
│   ├── goose-config.sh      ← Goose provider configuration
│   └── post-create.sh       ← Automated setup on container creation
├── scripts/
│   ├── ai                   ← ⭐ Stable interface (Runtime v5)
│   ├── adapters/
│   │   ├── _base.sh         ← Shared contract utilities (v2.1)
│   │   ├── ai.sh            ← Active adapter symlink
│   │   ├── goose.sh         ← Goose AI agent adapter
│   │   ├── mock.sh          ← Offline/testing adapter
│   │   ├── http-agent.sh    ← Dependency-free HTTP adapter (v4)
│   │   └── README.md
│   ├── mock-server/
│   │   ├── mock_openai.py   ← FastAPI OpenAI-compatible mock server
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── health-check.sh      ← Full system health with color output
│   ├── start-colab-proxy.sh ← Google Colab GPU setup
│   └── switch-model.sh      ← Provider switching (persists to .env)
├── runtime/
│   └── tool_executor.sh/py  ← Tool execution layer (Python)
├── skills/                  ← Agent Skills for managed projects
│   ├── agent-sim/SKILL.md
│   ├── arb-agent-system/SKILL.md
│   ├── private-ai-stack/SKILL.md
│   └── ai-dev-platform/SKILL.md
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   └── workflows.md
├── .env.example
└── Makefile
```

## The `ai` Script — Runtime v5

The stable interface. Contract-driven. Never changes.

```bash
# Commands
ai run      "analyze the agent-sim protocol layer"
ai fix      "ImportError in agent_runner.py line 42"
ai explain  "how does Q-learning convergence work"
ai refactor "simplify env_interface.py"
ai query    "what should I work on next"

# Flags
ai run --trace "task"           # Show execution steps
ai run --max-steps=5 "task"     # Limit execution loop
ai run --budget=3 "task"        # Max iterations
```

Runtime v5 features:
- JSON contract adapter protocol
- Tool execution loop with loop protection
- Budget and max-steps controls
- Timeout per adapter call (AI_TIMEOUT=30)
- Trace mode for debugging
- Legacy plain text adapter support

## Adapter Contract (JSON Protocol)

All adapters communicate via structured JSON:

```json
{ "status": "done",      "output": "result text" }
{ "status": "tool_call", "tool_call": { "name": "read_file", "input": {} } }
{ "status": "continue",  "next_input": "next prompt" }
{ "status": "error",     "output": "what went wrong" }
```

`_base.sh` provides shared utilities for all adapters:
- `build_response()` — standard JSON response builder
- `build_tool_call()` — tool call response builder
- `safe_build_response()` — never-fail fallback
- `classify_error()` — error type classification
- `json_valid()` — JSON validation
- `json_escape()` — safe string escaping
- `adapter_exit()` — always exits 0 (errors in payload, not exit code)

## Providers

| Provider | Command | Description |
|----------|---------|-------------|
| `openai` | `make openai` | OpenAI API |
| `colab` | `make colab` | Google Colab GPU via ngrok |
| `local` | `make local` | Local Ollama / private-ai-stack |
| `mock` | `make mock` | Offline mode — no AI calls |
| `mock-local` | `make mock-local` | Goose → local mock server |
| `http` | `make http` | Dependency-free curl adapter |

## Adapters

### goose.sh
Primary adapter. Wraps Goose CLI.
Uses `goose run --no-session -t "prompt"` syntax.
Injects ACTIVE_PROJECT context.
Falls back to http-agent.sh if Goose not installed.

### http-agent.sh (v4 production)
Dependency-free. Only needs curl + bash.
Retry loop with exponential backoff (3 retries default).
JSON mode support (AI_JSON_MODE=true).
Smart error classification — doesn't retry auth failures.

### mock.sh
No network. No AI calls.
Mirrors goose.sh interface exactly.
Perfect for planes, CI/CD, offline development.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `openai` | Active provider |
| `AI_ADAPTER` | `goose` | Active adapter |
| `MODEL_ENDPOINT` | provider default | API endpoint URL |
| `MODEL_NAME` | `gpt-4o-mini` | Model to use |
| `OPENAI_API_KEY` | — | Required for OpenAI |
| `COLAB_URL` | — | Required for Colab |
| `ACTIVE_PROJECT` | — | Context injection for AI |
| `AI_TIMEOUT` | `30` | Adapter call timeout (seconds) |
| `AI_RETRIES` | `3` | HTTP retry count |
| `MODEL_TEMPERATURE` | `0.7` | LLM temperature |
| `AI_JSON_MODE` | `false` | Force JSON response format |

## Mock Server

FastAPI OpenAI-compatible mock server for validation:

```bash
make mock-server-bg    # Start in background
make mock-server-test  # Test all endpoints
make mock-local        # Point Goose at it
make mock-server-stop  # Stop it
```

Endpoints: `/health`, `/v1/models`, `/v1/chat/completions`
Echoes full request debug info in responses.

## Validation Ladder

Tests each layer independently — isolates failures precisely:

```bash
make validate
# Step 1: mock adapter     → proves scripts/ai routes correctly
# Step 2: mock-local       → proves Goose → API call chain works
# Then: make local | make openai | make colab
```

## Project Context Switching

```bash
make ctx-agent-sim    # ACTIVE_PROJECT=agent-sim
make ctx-arb          # ACTIVE_PROJECT=arb-agent-system
make ctx-ai-stack     # ACTIVE_PROJECT=private-ai-stack
```

## Managed Projects

```
ai-dev-platform manages:
├── private-ai-stack    ← Local AI infrastructure (Kong + Ollama)
├── agent-sim           ← RL research framework
└── arb-agent-system    ← Financial multi-agent system
```

## Dev Container

Based on: `mcr.microsoft.com/devcontainers/base:ubuntu-22.04`

Includes:
- Python 3 + venv at /opt/venv
- Node.js 20
- Goose CLI (official install script)
- curl, git, jq, make, htop

Install Goose if missing:
```bash
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh \
  | CONFIGURE=false bash
# Requires bzip2: sudo apt-get install -y bzip2
```

## Goose Configuration

```bash
# Goose uses -t flag for non-interactive prompts:
goose run --no-session -t "your prompt"

# Configure provider:
goose configure  # interactive
# or via goose-config.sh which calls:
goose config set provider openai-compatible
goose config set base_url "http://endpoint/v1"
```

## Common Workflows

### Quick Start
```bash
git clone https://github.com/sparky10001/ai-dev-platform
# Open in VS Code → Reopen in Container
make setup
make mock-server-bg
make validate
make health
```

### Switch to local Ollama
```bash
make local
# Requires MODEL_ENDPOINT in .env pointing to Ollama instance
```

### Work on agent-sim
```bash
make ctx-agent-sim
ai run "what needs attention today?"
ai fix "the Q-agent convergence issue"
```

### Plane/offline mode
```bash
make mock
ai run "plan the LiteLLM integration"
# → [MOCK] Would run: plan the LiteLLM integration
```

## Roadmap

- [x] Stable ai interface (Runtime v5)
- [x] Goose, mock, http-agent adapters
- [x] _base.sh shared contract utilities
- [x] Provider switching (persists to .env)
- [x] Mock OpenAI server
- [x] Validation ladder
- [x] Health check system
- [x] Dev Container
- [x] Agent Skills (this folder!)
- [ ] tool_executor.py — Python tool execution layer
- [ ] Session persistence
- [ ] Project registry
- [ ] Web UI for provider management
- [ ] Colab GPU integration (ngrok + LiteLLM)
