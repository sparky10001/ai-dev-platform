# 🛠️ Setup Guide

This guide will get you up and running with the AI Dev Platform.

---

## ✅ Requirements

| Tool | Required | Install |
|------|----------|---------|
| Docker | ✅ Yes | [docker.com](https://docker.com) |
| VS Code | ✅ Yes | [code.visualstudio.com](https://code.visualstudio.com) |
| Dev Containers extension | ✅ Yes | VS Code Extensions → search "Dev Containers" |
| Goose | ✅ Yes | [block.github.io/goose](https://block.github.io/goose/docs/getting-started/installation) |
| Ollama | Optional | [ollama.ai](https://ollama.ai) — for local provider |

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform
```

### 2. Open in Dev Container

In VS Code:
- Press `Ctrl+Shift+P`
- Select **Dev Containers: Reopen in Container**
- Wait for the container to build (~2 minutes first time)
- `post-create.sh` runs automatically and configures everything

### 3. Configure your provider

```bash
make openai    # If you have an OpenAI API key
make local     # If you have Ollama running locally
make mock      # If you want to test without any AI
```

### 4. Verify everything works

```bash
make health
make status
```

### 5. Start building

```bash
ai run "let's get started"
```

---

## ⚙️ Manual Setup (without Dev Container)

```bash
# Clone
git clone https://github.com/sparky10001/ai-dev-platform.git
cd ai-dev-platform

# Setup
make setup

# Edit .env with your configuration
nano .env

# Switch to your provider
make openai

# Verify
make health
```

---

## 🔑 Provider Configuration

### OpenAI

```bash
# .env
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

```bash
make openai
```

### Google Colab GPU

1. Open a Colab notebook with GPU runtime
2. Run the LiteLLM proxy setup cell:

```python
# In your Colab notebook
!pip install litellm pyngrok
from pyngrok import ngrok
import subprocess

# Start LiteLLM proxy
subprocess.Popen(["litellm", "--model", "ollama/phi3", "--port", "8000"])

# Expose via ngrok
tunnel = ngrok.connect(8000)
print(f"Proxy URL: {tunnel.public_url}")
```

3. Copy the ngrok URL
4. Run:

```bash
make colab
# Paste your ngrok URL when prompted
```

### Local Ollama

```bash
# Ensure Ollama is running
ollama serve
ollama pull phi3

# .env
MODEL_PROVIDER=local
MODEL_ENDPOINT=http://localhost:11434/v1
# Or if running in Docker:
# MODEL_ENDPOINT=http://host.docker.internal:11434/v1
```

```bash
make local
```

### Offline / Mock Mode

No configuration needed — works anywhere including on a plane!

```bash
make mock
ai run "plan my next feature"
# → [MOCK] Would run: plan my next feature
```

---

## 🔧 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `openai` | Active provider: openai, colab, local, mock |
| `AI_ADAPTER` | `goose` | Active adapter: goose, mock |
| `MODEL_ENDPOINT` | provider default | Override API endpoint URL |
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `COLAB_URL` | — | Required for Colab provider |
| `GOOSE_MODEL` | provider default | Override model selection |
| `ACTIVE_PROJECT` | — | Current project context for AI |

---

## 🩺 Troubleshooting

**Adapter not found:**
```bash
make mock    # Safe fallback — always works
make status  # Check what's configured
```

**Goose not installed:**
```bash
curl -fsSL https://github.com/block/goose/releases/latest/download/goose-linux-x86_64 \
  -o /usr/local/bin/goose && chmod +x /usr/local/bin/goose
```

**Model endpoint not reachable:**
```bash
make health           # See what's failing
make mock             # Switch to offline while debugging
curl $MODEL_ENDPOINT  # Test manually
```

**Dev Container won't build:**
```bash
docker system prune   # Clean Docker cache
# Then reopen in container
```
