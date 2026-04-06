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
./scripts/ai run "your task"     ← Never changes
    │
    ▼
scripts/adapters/ai.sh           ← Swappable adapter
    │
    ▼
Goose │ Mock │ (your agent)      ← Replaceable agent
    │
    ▼
OpenAI │ Colab │ Local │ Mock    ← Replaceable model
```

Swap the agent. Swap the model. Swap the compute.
**Your workflow stays the same.**

---

## ✨ Features

- **Provider Agnostic** — OpenAI, Google Colab GPU, local Ollama, or mock offline mode
- **Agent Agnostic** — Goose today, anything tomorrow — adapter pattern enforces the contract
- **Portable** — Works at home, at work, on a plane, in a container
- **One Command Setup** — Dev Container handles everything automatically
- **Project Aware** — Switch context between projects instantly
- **Health Checks** — Know your stack is working before you start
- **Offline Mode** — Mock adapter keeps your workflow intact without internet

---

## 🚀 Quick Start

### Option 1 — Dev Container (Recommended)

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

Open in VS Code → **Reopen in Container**

Everything configures automatically. Then:

```bash
make status    # see active configuration
make health    # verify everything works
make openai    # configure your provider
ai run "let's build something"
```

### Option 2 — Local Setup

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
make setup
make openai    # or: make local | make mock
```

---

## 📋 Requirements

| Tool | Required | Notes |
|------|----------|-------|
| Docker | ✅ Yes | For Dev Container |
| VS Code | ✅ Yes | With Dev Containers extension |
| Goose | ✅ Yes | Primary AI agent |
| Ollama | Optional | For local model provider |
| OpenAI API Key | Optional | For OpenAI provider |
| Google Colab | Optional | For GPU compute |

---

## ⚡ The `ai` Command

Everything goes through one stable interface:

```bash
ai run      "analyze the agent-sim protocol layer"
ai fix      "ImportError in agent_runner.py line 42"
ai explain  "how does Q-learning convergence work"
ai refactor "simplify the env_interface.py adapter"
ai query    "what should I work on next"
```

**Same commands. Any provider. Any environment.**

---

## 🔄 Switching Providers

```bash
make openai    # OpenAI API
make colab     # Google Colab GPU (prompts for ngrok URL)
make local     # Local Ollama via private-ai-stack
make mock      # Offline mode — no AI calls
```

Or via environment variable:
```bash
MODEL_PROVIDER=local make ai-run CMD="review my code"
```

---

## 🌍 Environment Scenarios

### At Home — Local AI (private)
```bash
make local
# Uses Ollama via private-ai-stack
# No data leaves your network
ai run "review arb-agent-system risk service"
```

### At Work — OpenAI
```bash
make openai
# Uses OpenAI API
ai run "refactor agent-sim protocol layer"
```

### On a Plane — Offline
```bash
make mock
# No internet required
# Commands logged but not executed
ai run "plan my next feature"  # → [MOCK] Would run: plan my next feature
```

### Need GPU — Google Colab
```bash
make colab
# Prompts for ngrok URL from your Colab notebook
# Connects to GPU-accelerated LiteLLM proxy
ai run "train the Q-learning agent for 10000 episodes"
```

---

## 📁 Project Structure

```
ai-dev-platform/
├── .devcontainer/
│   ├── devcontainer.json    — VS Code Dev Container config
│   ├── Dockerfile           — Dev environment definition
│   ├── goose-config.sh      — Goose provider configuration
│   └── post-create.sh       — Automatic setup on container creation
├── scripts/
│   ├── ai                   — ⭐ Stable AI interface (never changes)
│   ├── adapters/
│   │   ├── ai.sh            — Active adapter symlink
│   │   ├── goose.sh         — Goose AI agent adapter
│   │   ├── mock.sh          — Offline/testing adapter
│   │   └── README.md        — Adapter documentation
│   ├── health-check.sh      — System health verification
│   ├── start-colab-proxy.sh — Google Colab GPU setup
│   └── switch-model.sh      — Provider switching
├── docs/
│   ├── architecture.md      — System design and principles
│   ├── setup.md             — Detailed setup guide
│   └── workflows.md         — Common usage patterns
├── .env.example             — Environment configuration template
├── Makefile                 — Unified command interface
└── README.md                — You are here!
```

---

## 🗺️ Roadmap

- [x] Stable `ai` command interface
- [x] Goose adapter
- [x] Mock offline adapter
- [x] OpenAI provider
- [x] Google Colab GPU provider
- [x] Local Ollama provider
- [x] Dev Container environment
- [x] Health check system
- [x] Provider switching
- [ ] Session persistence across container restarts
- [ ] Project registry — register and switch between projects
- [ ] Ollama direct adapter (without Goose)
- [ ] Claude adapter
- [ ] OpenAI adapter (direct, without Goose)
- [ ] Web UI for provider/project management
- [ ] CI/CD integration guide
- [ ] Multi-user team configuration

---

## 🤝 Adding Your Own Adapter

The adapter interface is simple — implement these commands:

```bash
#!/bin/bash
# your-agent.sh

COMMAND=$1
shift

case "$COMMAND" in
  run)      your_agent run "$@" ;;
  explain)  your_agent prompt "Explain: $@" ;;
  refactor) your_agent run "Refactor: $@" ;;
  fix)      your_agent run "Fix: $@" ;;
  query)    your_agent prompt "$@" ;;
  *)        echo "Unknown: $COMMAND" ;;
esac
```

Then activate it:
```bash
ln -sf scripts/adapters/your-agent.sh scripts/adapters/ai.sh
```

That's it. Your agent is now the active provider. 😄

---

## 🙏 Acknowledgments

- [Goose](https://block.github.io/goose/) — AI agent by Block
- [Ollama](https://ollama.ai/) — Local LLM runtime
- [private-ai-stack](https://github.com/sparky10001/private-ai-stack) — Local AI infrastructure
- [agent-sim](https://github.com/sparky10001/agent-sim) — LLM-native RL framework

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
Built with ❤️ by James R. Glines<br>
The interface is stable. Everything else is replaceable.
</p>
