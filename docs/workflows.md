# 🔄 Workflows

Common usage patterns for the AI Dev Platform.

---

## 🧠 Core Concept

All AI interactions go through one stable command:

```bash
ai <command> "<task>"
```

The provider underneath can change. Your workflow never does.

---

## 📋 Available Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `ai run` | General task execution | `ai run "analyze my codebase"` |
| `ai fix` | Fix a specific issue | `ai fix "TypeError in line 42"` |
| `ai explain` | Get an explanation | `ai explain "how does Q-learning work"` |
| `ai refactor` | Improve existing code | `ai refactor "simplify env_interface.py"` |
| `ai query` | Ask a question | `ai query "what should I build next"` |

---

## 🌍 Environment Workflows

### At Home — Private Local AI

```bash
make local
export ACTIVE_PROJECT=agent-sim

ai run "run the benchmark comparison and summarize results"
ai fix "the Q-agent isn't converging after 500 episodes"
ai explain "why is the reward shaping not working"
```

### At Work — OpenAI

```bash
make openai
export ACTIVE_PROJECT=arb-agent-system

ai run "review the risk service and suggest improvements"
ai refactor "orchestrator.py — reduce code duplication"
```

### On a Plane — Offline

```bash
make mock

# Commands are logged but not executed
# Great for planning and note-taking
ai run "plan the LiteLLM integration for agent-sim"
# → [MOCK] Would run: plan the LiteLLM integration for agent-sim
```

### GPU Tasks — Google Colab

```bash
make colab
# Paste ngrok URL when prompted

ai run "train Q-agent for 10000 episodes and report convergence"
ai run "run ULTRAPLINIAN benchmark across all models"
```

---

## 🔀 Project Context Switching

```bash
# Switch project context
make ctx-agent-sim
ai run "what's the next milestone?"

make ctx-arb
ai run "review the execution service"

make ctx-ai-stack
ai run "check Kong configuration"
```

---

## 🏥 Daily Health Check

```bash
# Start of every session
make health
make status

# If something is wrong
make mock     # fallback while debugging
make health   # re-check after fixing
```

---

## 🔌 Switching Providers Mid-Session

```bash
# Start with OpenAI
make openai
ai run "design the new feature"

# Switch to local for implementation (private)
make local
ai run "implement the feature we just designed"

# Switch to mock for testing
make mock
ai run "verify the implementation plan"
```

---

## 🧩 Managing Multiple Projects

```bash
# Register your projects in .env
AGENT_SIM_URL=http://localhost:8000
ARB_AGENT_URL=http://localhost:8080
PRIVATE_AI_STACK_URL=http://localhost:8001

# Health check covers all of them
make health

# Switch context and get AI help
make ctx-agent-sim
ai run "what needs attention today?"
```

---

## 💡 Tips

**Be specific with tasks:**
```bash
# Less effective
ai run "fix the bug"

# More effective
ai run "fix the ImportError in agent_sim/adapter/local_env.py line 23"
```

**Use project context:**
```bash
make ctx-agent-sim
ai run "review the protocol validator"
# Goose now knows you're in agent-sim context
```

**Chain commands:**
```bash
ai explain "the parity check failure" && \
ai fix "env_interface.py parity assertion at line 45"
```
