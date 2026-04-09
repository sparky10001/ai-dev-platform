# 🧪 Mock OpenAI Server

A minimal OpenAI-compatible API server for local testing and validation.

---

## Purpose

Validates that the full Goose → API call chain works correctly
without requiring a real AI provider, network, or GPU.

```
Dev Container
    └── Goose
            └── POST /v1/chat/completions
                        └── mock_openai.py  ← YOU ARE HERE
                                └── Returns mock response
```

---

## Usage

### Start the server

```bash
# From project root
make mock-server

# Or manually
cd scripts/mock-server
uvicorn mock_openai:app --host 0.0.0.0 --port 8000
```

### Switch Goose to use it

```bash
make mock-local
```

### Test it directly

```bash
# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/v1/models

# Chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}]}'
```

### Test via Goose

```bash
ai run "hello from mock server"
# → [MOCK SERVER] Received: hello from mock server
```

---

## What This Validates

| Check | What it proves |
|-------|---------------|
| Server starts | FastAPI + uvicorn work in container |
| `/v1/models` responds | Goose can discover models |
| `/v1/chat/completions` responds | Goose API call format is correct |
| Response parsed correctly | Goose handles the response |
| `ai run` works end to end | Full platform chain is working |

---

## Debugging

The mock server echoes back the full request context:

```json
{
  "choices": [{
    "message": {
      "content": "[MOCK SERVER] Received: your message\nDebug: {full request info}"
    }
  }]
}
```

If something breaks later with a real provider:

```bash
make mock-local     # Switch back to mock
ai run "test"       # If this works → problem is the provider
                    # If this fails → problem is the platform
```

---

## Validation Ladder

```
make mock           → mock.sh (no network)      → validates adapter
make mock-local     → mock_openai.py (local)    → validates API calls
make local          → Ollama (local GPU)         → validates local AI
make colab          → LiteLLM (remote GPU)       → validates Colab
make openai         → OpenAI (cloud)             → validates production
```

Work up the ladder. Each step adds one variable.
