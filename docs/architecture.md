# 🏗️ Architecture

## Core Principle

> **Only one thing is stable: the AI interface.**
> Everything else can change, will change, should be replaceable.

---

## Layers

```
┌─────────────────────────────────────┐
│         Developer                   │
│   ai run "your task"                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Interface Layer                │  ← STABLE — never changes
│   scripts/ai                        │
│   Single entry point for all AI     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Adapter Layer                  │  ← SWAPPABLE
│   scripts/adapters/*.sh             │
│                                     │
│   goose.sh  │  mock.sh  │  (yours)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Agent Layer                    │  ← REPLACEABLE
│                                     │
│   Goose  │  (Claude)  │  (OpenAI)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Model Layer                    │  ← REPLACEABLE
│                                     │
│  OpenAI │ Colab GPU │ Local │ Mock  │
└─────────────────────────────────────┘

---

## Component Responsibilities

### Interface Layer — `scripts/ai`
- **Never changes**
- Loads environment
- Validates command
- Delegates to active adapter
- Single source of truth for all AI interactions

### Adapter Layer — `scripts/adapters/`
- Translates interface commands to agent-specific calls
- Adding a new agent = adding a new adapter file
- All adapters implement the same command set

### Agent Layer — Goose, etc.
- The actual AI agent that processes requests
- Completely replaceable without changing interface or adapters
- Configured via `goose-config.sh`

### Model Layer — OpenAI, Colab, Local
- The LLM that powers the agent
- Switched via `switch-model.sh`
- Configured via `.env`

---

## Request Flow

```
Developer types:
  ai fix "broken import in agent_runner.py"

scripts/ai:
  1. Loads .env
  2. Validates command ("fix")
  3. Resolves adapter via AI_ADAPTER (e.g., goose)
  4. Calls: scripts/adapters/goose.sh fix "broken import..."

goose.sh:
  5. Injects project context if ACTIVE_PROJECT set
  6. Calls: goose run "[Project: agent-sim] Fix: broken import..."

Goose:
  7. Sends to configured model endpoint
  8. Returns response

Developer sees result.
```

---

## Provider Configuration Flow

```
make local
    │
    ▼
switch-model.sh local
    │
    ├── Updates .env:
    │     MODEL_PROVIDER=local
    │     MODEL_ENDPOINT=http://host.docker.internal:11434/v1
    │     AI_ADAPTER=goose
    │
    └── Calls goose-config.sh:
          goose config set provider openai-compatible
          goose config set base_url http://host.docker.internal:11434/v1
```

---

## Managed Projects

```
ai-dev-platform
    │
    ├── private-ai-stack    ← Local AI infrastructure
    │     Kong + Ollama + OpenClaw
    │
    ├── agent-sim           ← RL research framework
    │     Protocol API + GridWorld + Q-learning
    │
    └── arb-agent-system    ← Financial multi-agent system
          FastAPI + PostgreSQL + ccxt
```

---

## Design Goals

| Goal | How Achieved |
|------|-------------|
| Tool agnostic | Adapter pattern — swap goose.sh for any agent |
| Provider agnostic | switch-model.sh updates config, not code |
| Portable | Dev Container — identical everywhere |
| Offline capable | mock.sh adapter — works on planes |
| Project aware | ACTIVE_PROJECT context injection |
| Self-documenting | make help, README, docs/ |

---

## Adding a New Adapter

1. Create `scripts/adapters/your-agent.sh`
2. Implement: `run`, `explain`, `refactor`, `fix`, `query`
3. Activate via .env:
4. Add `make your-agent` target to Makefile

**No other files change. The interface is stable.**
