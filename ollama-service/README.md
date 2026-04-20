# 🦙 Ollama Service Container

Local LLM inference service for ai-dev-platform.
Runs tinyllama by default. OpenAI-compatible API.

---

## Quick Start

```bash
# Build and start
docker compose up --build

# Start in background
docker compose up --build -d

# Check logs
docker compose logs -f ollama

# Run validation test
docker compose --profile test up ollama-test
```

---

## What Happens on First Start

```
1. Official ollama/ollama image starts
2. Ollama server starts in background
3. Waits until server is ready (up to 60s)
4. Pulls tinyllama (~638MB) if not already present
5. Lists available models
6. Server ready on port 11434
```

Models are stored in a named Docker volume — **not re-downloaded on rebuild**!

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tags` | GET | List available models |
| `/api/generate` | POST | Generate (Ollama native) |
| `/api/chat` | POST | Chat (Ollama native) |
| `/v1/chat/completions` | POST | OpenAI-compatible chat |
| `/v1/models` | GET | OpenAI-compatible model list |

---

## Test Manually

```bash
# Health check
curl http://localhost:11434/api/tags

# Generate (Ollama native)
curl http://localhost:11434/api/generate \
  -d '{"model":"tinyllama","prompt":"Hello!","stream":false}'

# Chat (OpenAI-compatible)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"tinyllama","messages":[{"role":"user","content":"Hello!"}]}'
```

---

## Add More Models

**Via environment variable (pulled on startup):**
```bash
# .env
EXTRA_MODELS=phi3,llama3.2
```

**Via docker exec (running container):**
```bash
docker exec ollama ollama pull phi3
docker exec ollama ollama list
```

**Available small models for CPU:**

| Model | Size | RAM Needed | Notes |
|-------|------|------------|-------|
| `tinyllama` | ~638MB | ~1GB | Default — fastest |
| `phi3:mini` | ~2.2GB | ~3GB | Better reasoning |
| `llama3.2:1b` | ~1.3GB | ~2GB | Good balance |
| `gemma:2b` | ~1.7GB | ~2.5GB | Google model |

---

## Integration with ai-dev-platform

**In ai-dev-platform `.env`:**
```bash
MODEL_PROVIDER=local
OLLAMA_ENDPOINT=http://ollama:11434
OLLAMA_MODEL=tinyllama
AI_ADAPTER=ollama
```

**Or via switch-model:**
```bash
make ollama
# Sets OLLAMA_ENDPOINT and AI_ADAPTER=ollama
```

**In ai-dev-platform `docker-compose.yml` — add as external service:**
```yaml
services:
  ai-platform:
    # ... your existing config
    environment:
      - OLLAMA_ENDPOINT=http://ollama:11434
    depends_on:
      - ollama

  # Include Ollama service
  ollama:
    extends:
      file: ./ollama-service/docker-compose.yml
      service: ollama
```

---

## Resource Notes

**Default limits (tuned for Y510P 8GB RAM):**
- Memory limit: 4GB
- Memory reserve: 1GB
- tinyllama uses ~1GB RAM during inference

**If container runs out of memory:**
```bash
# Reduce limit in .env:
OLLAMA_MEMORY_LIMIT=3g

# Or unload model between requests:
OLLAMA_KEEP_ALIVE=0
```

---

## Volume Management

```bash
# List volumes
docker volume ls | grep ollama

# Inspect volume (find where models are stored)
docker volume inspect ai-dev-platform-ollama-models

# Remove volume (forces model re-download)
docker volume rm ai-dev-platform-ollama-models

# Backup models to host
docker run --rm \
  -v ai-dev-platform-ollama-models:/models \
  -v $(pwd):/backup \
  alpine tar czf /backup/ollama-models-backup.tar.gz /models
```

---

## Troubleshooting

**Container exits immediately:**
```bash
docker compose logs ollama
# Usually: model pull failed or OOM
```

**Model pull fails:**
```bash
# Check network connectivity from container
docker exec ollama curl -I https://registry.ollama.ai
# If blocked: pre-pull on host, copy to volume
```

**Slow inference:**
```bash
# Normal for CPU — tinyllama: ~10-30 tokens/sec on modern CPU
# Set thread count explicitly:
OLLAMA_NUM_THREAD=4  # Match your CPU cores
```

**Out of memory during inference:**
```bash
# Add swap space on Ubuntu VM:
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
