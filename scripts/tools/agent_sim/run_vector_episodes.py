#!/usr/bin/env python3
###################################################################
# run_vector_episodes.py — Run parallel agent-sim environments (MCP-compliant v1.0)
#
# Purpose:
#   Executes multiple GridWorld environments in parallel using SyncVectorEnv
#   and returns structured performance statistics + replay info.
###################################################################

import os
import sys
from pathlib import Path
from typing import Any, Dict

# ================================================================
# 🧾 TOOL METADATA (REQUIRED FOR v8+)
# ================================================================

name = "run_vector_episodes"
description = "Run multiple parallel GridWorld environments using SyncVectorEnv and return performance metrics"

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "num_envs": {
            "type": "integer",
            "description": "Number of parallel environments to run",
            "default": 4
        },
        "episodes": {
            "type": "integer",
            "description": "Number of episodes per environment",
            "default": 50
        },
        "max_steps": {
            "type": "integer",
            "description": "Maximum steps per episode",
            "default": 100
        },
        "agent_type": {
            "type": "string",
            "enum": ["q_agent", "random", "stub"],
            "description": "Agent type to use",
            "default": "q_agent"
        },
        "seed": {
            "type": "integer",
            "description": "Random seed for reproducibility",
            "default": None
        }
    }
}

# ================================================================
# 🧱 RESPONSE HELPERS
# ================================================================

def success(data: Dict, meta=None):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "meta": meta or {}
    }

def failure(message: str, error_type="tool_error", meta=None):
    return {
        "status": "error",
        "data": None,
        "error": {
            "message": message,
            "type": error_type
        },
        "meta": meta or {}
    }

# ================================================================
# 🔗 AGENT-SIM INTEGRATION
# ================================================================

ROOT_DIR = Path(__file__).resolve().parents[3]
AGENT_SIM_PATH = ROOT_DIR / "agent-sim"

if str(AGENT_SIM_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_SIM_PATH))

try:
    from agent_sim.runners.vector_env import SyncVectorEnv
    from agent_sim.envs.gridworld import GridWorldEnv
    # from agent_sim.agents.q_agent import QAgent  # TODO: wire in real agent later
except ImportError as e:
    print(f"Failed to import agent-sim: {e}", file=sys.stderr)
    sys.exit(1)

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data: Dict[str, Any]):
    try:
        num_envs = int(input_data.get("num_envs", 4))
        episodes = int(input_data.get("episodes", 50))
        max_steps = int(input_data.get("max_steps", 100))
        agent_type = input_data.get("agent_type", "q_agent")
        seed = input_data.get("seed")

        if num_envs < 1 or episodes < 1 or max_steps < 1:
            return failure("num_envs, episodes, and max_steps must be positive", "validation_error")

        # Create environment factories
        def make_env():
            return GridWorldEnv(max_steps=max_steps)

        env_fns = [make_env for _ in range(num_envs)]
        vector_env = SyncVectorEnv(env_fns)

        total_reward = 0.0
        completed = 0

        for ep in range(episodes):
            states = vector_env.reset(seed=seed + ep if seed is not None else None)
            done_flags = [False] * num_envs
            episode_rewards = [0.0] * num_envs

            step = 0
            while step < max_steps and not all(done_flags):
                # Placeholder: Replace with proper agent selection + action logic
                actions = ["right"] * num_envs

                states, rewards, dones, infos = vector_env.step(actions)

                for i in range(num_envs):
                    if not done_flags[i]:
                        episode_rewards[i] += float(rewards[i])
                        if dones[i]:
                            done_flags[i] = True
                            completed += 1
                step += 1

            total_reward += sum(episode_rewards)

        vector_env.close()

        avg_reward = total_reward / (num_envs * episodes) if episodes > 0 else 0.0
        success_rate = completed / (num_envs * episodes) if episodes > 0 else 0.0

        result = {
            "num_envs": num_envs,
            "episodes": episodes,
            "agent_type": agent_type,
            "max_steps": max_steps,
            "avg_reward": round(avg_reward, 4),
            "success_rate": round(success_rate, 4),
            "completed_episodes": completed,
            "total_steps": num_envs * episodes * max_steps
        }

        return success(result, meta={"tool": "run_vector_episodes"})

    except Exception as e:
        return failure(f"Vector episode execution failed: {str(e)}", "execution_error")


# For quick local testing
if __name__ == "__main__":
    test_input = {"num_envs": 2, "episodes": 10, "max_steps": 50}
    result = run(test_input)
    print(result)