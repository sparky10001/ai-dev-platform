---
name: agent-sim
description: >
  Use this skill when working on agent-sim — an LLM-native reinforcement
  learning framework with a protocol-first API, Q-learning agents, chaos
  testing, parity validation, replay logging, and multi-VM Docker architecture.
  Activate when the user mentions agent-sim, GridWorld, Q-learning, RL agents,
  protocol validator, replay logger, or environment adapters.
---

# agent-sim

> "The protocol is the contract. Everything else is replaceable."

## Project Overview

agent-sim is an open source LLM-native reinforcement learning framework.
It provides a standardized HTTP protocol API for training and evaluating
AI agents — from random baselines to Q-learning to LLM-driven agents.

- GitHub: https://github.com/sparky10001/agent-sim
- Language: Python (92.9%), Dockerfile (7.1%)
- License: MIT

## Core Principle

The environment exposes a clean protocol. Agents talk HTTP.
Nothing inside the agent knows how the environment works.
Nothing inside the environment knows how the agent works.
The protocol is the only contract.

## Architecture

```
runners/
  agent_runner.py          ← Main entry point. Orchestrates episodes.

agent_sim/
  adapter/
    env_interface.py       ← Abstract base class for all environments
    local_env.py           ← Runs GridWorld in-process (no network)
    remote_env.py          ← Calls Flask API over HTTP
  environments/
    gridworld.py           ← 5x5 grid, start (0,0), goal (4,4)
  protocol/
    env.py                 ← to_observation(), validate_state()
  replay/
    replay.py              ← ReplayLogger — writes .jsonl to mounted volume
    loader.py              ← Loads run files for analysis
    summarize.py           ← Prints episode summary stats
    renderer.py            ← Visual replay rendering
  server/
    server.py              ← Flask API server
  validation/
    protocol_validator.py  ← Full protocol contract test suite

agents/
  q_agent.py               ← Q-learning agent with epsilon-greedy exploration

services/
  llm_client.py            ← LLM abstraction stub (ready for Ollama)

docker/
  vm1/                     ← Orchestrator (agent_runner)
  vm2/                     ← Decision Hub (agents + LLM)
  vm3/                     ← LLM layer (LiteLLM + Ollama)

evals/                     ← Evaluation results and benchmarks
config/                    ← Environment configuration files
```

## Protocol API

All agents interact with the environment through these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Liveness check — always fast |
| `/v1/reset` | POST | Reset environment, returns initial state |
| `/v1/step` | POST | Apply action, returns state/reward/done |
| `/v1/metrics` | GET | Runtime episode metrics |

### State Schema
```json
{
  "x": 0,
  "y": 0,
  "goal": [4, 4]
}
```

### Step Request
```json
{ "action": "right" }
```

### Step Response
```json
{
  "state": { "x": 1, "y": 0, "goal": [4, 4] },
  "reward": 0.8,
  "done": false
}
```

Valid actions: `up`, `down`, `left`, `right`
Invalid action returns: HTTP 400

## GridWorld Environment

- Grid: 5x5
- Start position: (0, 0) — top left
- Goal position: (4, 4) — bottom right
- Reward shaping:
  - Goal reached: +20
  - Moving closer: positive (old_dist - new_dist) - 0.2
  - Moving away: negative
- Episode ends when goal reached or max_steps exceeded

## Environment Modes

```bash
# Local mode — runs GridWorld directly in process (no Docker needed)
ENV_MODE=local python -m agent_sim.runner.agent_runner

# Remote mode — calls Flask API over HTTP
ENV_MODE=remote BASE_URL=http://localhost:8000/v1 python -m agent_sim.runner.agent_runner

# Docker — spins up env server + agent runner
docker compose up --build
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV_MODE` | `local` | `local` or `remote` |
| `BASE_URL` | `http://localhost:8000/v1` | API endpoint for remote mode |
| `POLICY` | `random` | `random`, `greedy`, `q` |
| `EPSILON` | `1.0` | Q-agent exploration rate |
| `ALPHA` | `0.5` | Q-agent learning rate |
| `TRAIN_EPISODES` | `200` | Training episodes |
| `EVAL_EPISODES` | `20` | Evaluation episodes |
| `MAX_STEPS` | `50` | Max steps per episode |
| `LOG_DIR` | `/app/logs/runs` | Where replay logs are written |
| `ENABLE_PROTOCOL_CHECK` | `true` | Run validator at startup |
| `ENABLE_PARITY` | `true` | Enable parity testing |
| `ENABLE_CHAOS` | `false` | Enable chaos injection |
| `ENV_STRICT` | `false` | Fail hard on validation errors |

## Benchmark Results

| Agent | Success Rate | Avg Steps | Notes |
|-------|-------------|-----------|-------|
| Random | 20% | 48.4 | Baseline |
| Greedy | 100% | 8.0 | Hardcoded optimal path |
| Q-Learning (train) | 95% | 13.7 | After 200 episodes |
| Q-Learning (eval) | 100% | 8.0 | Greedy policy post-training |
| LLM (Phi-3) | TBD | TBD | Next milestone |

## Agent Architecture

### QAgent (agents/q_agent.py)
- State key: (dx, dy) — relative position to goal
- ε-greedy exploration with decay
- Epsilon hard stop at 0.02 → 0.0
- LLM hook placeholders ready (should_use_llm, llm_decide)
- train_then_greedy() pattern: train with ε > 0, evaluate with ε = 0

### ParityEnv
Runs local and remote environments simultaneously.
Asserts identical state/reward/done at every step.
Proves the two implementations are equivalent.

### ChaosEnv
Wraps any env and randomly injects failures.
Default failure rate: 5%.
Tests retry logic and graceful degradation.

## Replay System

Every episode is logged to JSONL format:
```
~/agent-sim/logs/runs/run_YYYYMMDD_HHMMSS.jsonl
```

Each file contains:
- Line 1: metadata header (type: "meta")
- Subsequent lines: one JSON object per step

```bash
# Summarize a run
python -m agent_sim.replay.summarize ~/agent-sim/logs/runs/run_*.jsonl
```

## Docker Volume Mount

Logs persist to the VM host — not inside the container:
```yaml
# docker-compose.yml
volumes:
  - ~/agent-sim/logs:/app/logs
environment:
  - LOG_DIR=/app/logs/runs
```

## Protocol Validation

Runs automatically at startup when ENABLE_PROTOCOL_CHECK=true.
Can also run manually:
```bash
python -m agent_sim.validation.protocol_validator
# Or against a remote server:
BASE_URL=http://192.168.163.135:8000/v1 python -m agent_sim.validation.protocol_validator
```

Validates: health, reset, step (all actions), invalid action rejection, determinism.

## Common Tasks

```bash
# Run random baseline
POLICY=random python -m agent_sim.runner.agent_runner

# Run Q-learning benchmark
POLICY=q TRAIN_EPISODES=500 python -m agent_sim.runner.agent_runner

# Validate protocol
python -m agent_sim.validation.protocol_validator

# Start Docker stack
docker compose up --build

# Check logs
ls ~/agent-sim/logs/runs/
python -m agent_sim.replay.summarize ~/agent-sim/logs/runs/run_latest.jsonl
```

## Next Milestones

- Wire Ollama into llm_client.py (Phi-3 vs Q-learning comparison)
- ULTRAPLINIAN multi-model evaluation
- STM output normalization for LLM action parsing
- AutoTune adaptive exploration parameters
- Three-VM deployment (VM1=Orchestrator, VM2=Decision Hub, VM3=LiteLLM+Ollama)

## Lab Environment

- Ubuntu Server 22.04 VM (192.168.163.129)
- Docker + docker compose
- Logs at: ~/agent-sim/logs/runs/
- Repo at: ~/agent-sim/repos/agent-sim/
