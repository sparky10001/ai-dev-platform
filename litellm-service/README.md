# 🔀 LiteLLM Service

AI request router for ai-dev-platform.
One OpenAI-compatible API. Any model. Automatic fallback.

---

## What It Does

```
Your request → LiteLLM → ollama/tinyllama  (local, free)
                       → openai/gpt-4.1    (cloud, smart)
                       → anthropic/claude  (cloud, powerful)
```

One endpoint. Intent-based routing. Automatic fallback if a provider fails.

---

## Quick Start

```bash
cd litellm-service
cp .env.example .env
make up
make test
```

---

## Model Aliases

| Alias | Primary | Fallback | Use When |
|-------|---------|----------|----------|
| `fast` | tinyllama (local) | — | Quick queries, always available |
| `general` | tinyllama (local) | — | Default, unclassified tasks |
| `code` | gpt-4.1 (OpenAI) | tinyllama | Code generation, debugging |
| `tooling` | gpt-4.1 (OpenAI) | tinyllama | Tool use, file operations |
| `claude` | claude-sonnet (Anthropic) | tinyllama | Complex reasoning |
| `smart` | gpt-4.1 → claude → tinyllama | — | Best available model |

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health |
| `GET /v1/models` | List available model aliases |
| `POST /v1/chat/completions` | Chat (OpenAI-compatible) |

All requests require:
```
Authorization: Bearer ai-dev-platform
```
(configurable via `LITELLM_MASTER_KEY`)

---

## Usage

```bash
# Fast local query (tinyllama)
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ai-dev-platform" \
  -d '{"model":"fast","messages":[{"role":"user","content":"hello"}]}'

# Code task (gpt-4.1 → tinyllama fallback)
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ai-dev-platform" \
  -d '{"model":"code","messages":[{"role":"user","content":"fix this bug"}]}'

# Best available model
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ai-dev-platform" \
  -d '{"model":"smart","messages":[{"role":"user","content":"complex task"}]}'
```

---

## Integration with ai-dev-platform

**In ai-dev-platform `.env`:**
```bash
LITELLM_BASE_URL=http://litellm:4000/v1
LITELLM_MASTER_KEY=ai-dev-platform
ACTIVE_MODEL=fast
AI_ADAPTER=litellm
```

**Switch model alias:**
```bash
# In ai-dev-platform
./scripts/switch-model.sh litellm-fast    # tinyllama
./scripts/switch-model.sh litellm-code    # gpt-4.1
./scripts/switch-model.sh litellm-claude  # claude-sonnet
```

---

## Network Architecture

LiteLLM joins two Docker networks:
- `ai-dev-platform-litellm-net` — for ai-dev-platform to reach LiteLLM
- `ai-dev-platform-ollama-net` — so `http://ollama:11434` resolves via Docker DNS

```
ai-dev-platform container
    └── http://litellm:4000  (litellm-net)
            └── LiteLLM
                    └── http://ollama:11434  (ollama-net, Docker DNS)
                    └── https://api.openai.com  (internet)
                    └── https://api.anthropic.com  (internet)
```

**This means `http://ollama:11434` is portable** — works on any machine
that runs both services, no hardcoded IPs needed! 😄

---

## Enabling Cloud Models

**OpenAI:**
```bash
# In .env
OPENAI_API_KEY=sk-your-key-here
ACTIVE_MODEL=code
```

**Anthropic/Claude:**
```bash
# In .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
ACTIVE_MODEL=claude
```

Cloud models automatically fall back to tinyllama if the key is missing
or the API call fails — so the platform always works! ✅

---

## Switching Active Model

```bash
make model-fast    # tinyllama (default)
make model-code    # gpt-4.1
make model-claude  # claude-sonnet
make model-smart   # best available
```

Or set `ACTIVE_MODEL` in `.env` and restart:
```bash
ACTIVE_MODEL=code docker compose restart litellm
```

---

## Troubleshooting

**LiteLLM can't reach Ollama:**
```bash
# Verify both are on the same network
docker network inspect ai-dev-platform-ollama-net

# Ensure Ollama is running first
cd ../ollama-service && make up
cd ../litellm-service && make up
```

**Auth error (401):**
```bash
# Check master key matches
grep LITELLM_MASTER_KEY .env
# Use in requests: Authorization: Bearer <your-key>
```

**Model not found:**
```bash
# Check available aliases
curl -sf http://localhost:4000/v1/models \
  -H "Authorization: Bearer ai-dev-platform"
```
