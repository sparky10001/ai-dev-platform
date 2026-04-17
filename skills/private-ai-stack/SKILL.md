---
name: private-ai-stack
description: >
  Use this skill when working on private-ai-stack — a one-command private
  AI infrastructure stack combining Kong API Gateway, Ollama local LLM runtime,
  and OpenClaw. Activate when the user mentions private-ai-stack, Kong, Ollama,
  OpenClaw, API gateway, local LLM hosting, or self-hosted AI infrastructure.
---

# private-ai-stack

> "Privacy first. One command. Everything replaceable."

## Project Overview

private-ai-stack is a one-command private AI deployment stack.
It combines Kong API Gateway, Ollama local LLM runtime, and OpenClaw
into a fully self-hosted, private AI infrastructure.

- GitHub: https://github.com/sparky10001/private-ai-stack
- License: MIT

## Core Philosophy

All AI inference stays local. No data leaves your network.
Kong provides the API gateway layer — routing, rate limiting, auth.
Ollama runs the models locally.
OpenClaw is the AI assistant layer.

## Stack Components

| Component | Role | Port |
|-----------|------|------|
| Kong API Gateway | API routing, rate limiting, authentication | 8000 (proxy), 8001 (admin) |
| Ollama | Local LLM runtime | 11434 |
| OpenClaw | AI assistant interface | varies |

## Project Structure

```
private-ai-stack/
├── install.sh           ← One-command installer
├── docker-compose.yml   ← Full stack definition
├── config/
│   └── kong.yml         ← Kong declarative config
├── Makefile             ← Control surface
├── .env.example         ← Environment template
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

## Quick Start

```bash
# One command — starts everything
./install.sh

# Or via make
make up
make down
make status
```

## Kong Configuration

Kong is configured declaratively via `config/kong.yml`.
Routes all AI requests through the gateway layer.

```bash
# Kong admin API
curl http://localhost:8001/services
curl http://localhost:8001/routes

# Test via Kong proxy
curl http://localhost:8000/api/generate \
  -d '{"model": "phi3", "prompt": "hello"}'
```

## Ollama Models

```bash
# Pull a model
docker exec ollama ollama pull phi3

# List available models
docker exec ollama ollama list

# Test directly
curl http://localhost:11434/api/generate \
  -d '{"model": "phi3", "prompt": "hello", "stream": false}'
```

## Lab Environment

- VM: Ubuntu Server 22.04 (kong-lab, 192.168.163.135)
- Host: Lenovo Y510P, Windows 10, 8GB RAM
- VMware Workstation Pro
- Phi-3 Mini model (2.2GB) installed
- K3s Kubernetes installed

## Ecosystem Role

private-ai-stack provides the LOCAL LLM INFERENCE layer for the full ecosystem:

```
ai-dev-platform
    └── make local → MODEL_ENDPOINT=http://192.168.163.135:11434/v1
            └── Goose → Kong API Gateway → Ollama → Phi-3
```

Also used by agent-sim as the LLM provider for the upcoming
LLM agent benchmark (Phi-3 vs Q-learning comparison).

## GitHub Topics

docker, privacy, ai, api-gateway, self-hosted, kong, homelab, llm, ollama, openclaw

## Common Tasks

```bash
# Start full stack
./install.sh
# or
docker compose up -d

# Check Kong is running
curl http://localhost:8001/status

# Test Ollama
curl http://localhost:11434/api/tags

# Test via Kong gateway
curl http://localhost:8000/

# Pull new model
docker exec ollama ollama pull llama3.2
```

## Integration with ai-dev-platform

When using private-ai-stack as the local provider:

```bash
# In ai-dev-platform .env
MODEL_PROVIDER=local
MODEL_ENDPOINT=http://192.168.163.135:11434/v1
```

```bash
make local
ai run "your task"
```
