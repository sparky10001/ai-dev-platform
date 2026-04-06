# 🔌 Adapters

Adapters are the bridge between the stable `ai` interface and specific AI agents.

---

## Active Adapter

`ai.sh` is a symlink pointing to the currently active adapter:

```bash
ls -la scripts/adapters/ai.sh
# ai.sh -> goose.sh   (currently using Goose)
# ai.sh -> mock.sh    (offline mode)
```

Switch adapters via:
```bash
make openai    # → goose.sh
make local     # → goose.sh (with local endpoint)
make mock      # → mock.sh
```

---

## Available Adapters

### `goose.sh` — Goose AI Agent
Primary adapter. Wraps Goose with project context injection.
Requires Goose to be installed.

### `mock.sh` — Offline Mock
Mirrors goose.sh interface exactly.
No AI calls made — logs intended actions only.
Perfect for: planes, CI/CD, testing.

---

## Command Interface

All adapters implement the same commands:

| Command | Purpose |
|---------|---------|
| `run` | Execute a general task |
| `fix` | Fix a specific issue |
| `explain` | Get an explanation |
| `refactor` | Improve existing code |
| `query` | Ask a question |

---

## Adding Your Own Adapter

```bash
#!/bin/bash
# scripts/adapters/my-agent.sh

COMMAND=$1
shift

case "$COMMAND" in
  run)      my_agent "$@" ;;
  fix)      my_agent "Fix: $@" ;;
  explain)  my_agent "Explain: $@" ;;
  refactor) my_agent "Refactor: $@" ;;
  query)    my_agent "$@" ;;
  *)        echo "Unknown: $COMMAND"; exit 1 ;;
esac
```

Activate it:
```bash
chmod +x scripts/adapters/my-agent.sh
ln -sf adapters/my-agent.sh scripts/adapters/ai.sh
```

**The interface is stable. Everything else is replaceable.**
