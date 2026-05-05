#!/usr/bin/env python3
###################################################################
# agent.py — Production Agent (v4.1 STABLE)
#
# Fixes:
# - Added missing _AGENT_CACHE
# - Hardened YAML loading (never returns None)
# - Safe agent fallback
# - Improved path resolution
###################################################################

import os
import sys
import json
import time
import yaml
import requests
import subprocess

from router import route

# ================================================================
# ⚙️ CONFIG
# ================================================================
BASE_URL = os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1")
MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "ai-dev-platform")

DEFAULT_MODEL = "balanced"
MAX_STEPS = int(os.getenv("AI_MAX_STEPS", "4"))
TIMEOUT = int(os.getenv("AI_TIMEOUT", "60"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

TOOL_EXECUTOR = os.path.join(SCRIPT_DIR, "tool_executor.py")

# ✅ FIX: initialize cache
_AGENT_CACHE = {}

# ================================================================
# 🧠 MODEL RESOLUTION
# ================================================================
def resolve_model(cli_model):
    if not cli_model:
        return os.getenv("ACTIVE_MODEL", DEFAULT_MODEL)

    cli_model = cli_model.lower().strip()

    if cli_model in ["fast", "balanced", "heavy"]:
        return cli_model

    return DEFAULT_MODEL

# ================================================================
# 🧾 RESPONSE CONTRACT
# ================================================================
def respond(status, output, meta=None):
    return {
        "status": status,
        "output": output,
        "meta": {
            "adapter": "agent.py",
            **(meta or {})
        }
    }

def done(output, meta=None):
    return respond("done", output, meta)

def error(msg):
    return respond("error", msg)

# ================================================================
# 📦 AGENT SPEC LOADING
# ================================================================
def load_agent_spec(command):
    agent_name = (os.getenv("AI_AGENT") or command or "default").lower()

    if agent_name in _AGENT_CACHE:
        return _AGENT_CACHE[agent_name]

    base_dir = os.path.join(ROOT_DIR, "agents")
    path = os.path.join(base_dir, f"{agent_name}.yaml")

    if not os.path.exists(path):
        path = os.path.join(base_dir, "default.yaml")

    try:
        with open(path, "r") as f:
            spec = yaml.safe_load(f) or {}
    except Exception:
        spec = {}

    # ✅ Guarantee minimum structure
    if not isinstance(spec, dict):
        spec = {}

    spec.setdefault("name", agent_name)
    spec.setdefault("mission", "")
    spec.setdefault("rules", [])
    spec.setdefault("process", [])
    spec.setdefault("style", {})

    _AGENT_CACHE[agent_name] = spec
    return spec


def build_system_prompt(spec: dict) -> str:
    if not isinstance(spec, dict):
        return "You are a helpful AI assistant."

    parts = []

    # ------------------------------------------------------------
    # 🎯 Mission
    # ------------------------------------------------------------
    mission = spec.get("mission")
    if isinstance(mission, str) and mission.strip():
        parts.append(f"Mission:\n{mission.strip()}")

    # ------------------------------------------------------------
    # 📏 Rules
    # ------------------------------------------------------------
    rules = spec.get("rules")
    if isinstance(rules, list) and rules:
        parts.append("Rules:\n" + "\n".join(f"- {r}" for r in rules if r))

    # ------------------------------------------------------------
    # 🧠 Process
    # ------------------------------------------------------------
    process = spec.get("process")
    if isinstance(process, list) and process:
        parts.append("Process:\n" + "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(process) if step
        ))

    # ------------------------------------------------------------
    # 🎨 Style
    # ------------------------------------------------------------
    style = spec.get("style")
    if isinstance(style, dict) and style:
        parts.append("Style:\n" + "\n".join(
            f"{k}: {v}" for k, v in style.items() if v
        ))

    # ------------------------------------------------------------
    # ⚙️ SYSTEM EXECUTION RULES (NON-NEGOTIABLE)
    # ------------------------------------------------------------
    parts.append(
        "Execution Rules:\n"
        "- If the task is answerable, provide a direct answer\n"
        "- Ask clarifying questions only if necessary\n"
        "- Do not ask more than 2 questions before answering\n"
        "- Prefer making reasonable assumptions over blocking\n"
        "- Do not stall or loop indefinitely\n"
        "- Always produce a final answer within a few steps\n"
    )

    return "\n\n".join(parts).strip()


# ================================================================
# 🌐 LLM CALL
# ================================================================
def call_llm(messages, model, tools):
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0
    }

    last_err = None

    for attempt in range(3):
        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {MASTER_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=TIMEOUT
            )

            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text}"
                time.sleep(1.5 * (attempt + 1))
                continue

            data = resp.json()

            if "choices" not in data:
                last_err = "Invalid LLM response"
                continue

            return data, None

        except Exception as e:
            last_err = str(e)
            time.sleep(1.5 * (attempt + 1))

    return None, last_err or "LLM failed"


# ================================================================
# 🔌 TOOL EXECUTION
# ================================================================
def run_tool(name, args):
    try:
        proc = subprocess.run(
            ["python3", TOOL_EXECUTOR, name, json.dumps(args)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if proc.returncode != 0:
            return {"status": "error", "error": proc.stderr}

        return json.loads(proc.stdout)

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ================================================================
# 🧰 TOOL DISCOVERY
# ================================================================
def load_tools():
    try:
        proc = subprocess.run(
            ["python3", TOOL_EXECUTOR, "--list-tools-openai"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if proc.returncode != 0:
            return []

        data = json.loads(proc.stdout)
        return data.get("tools", [])

    except Exception:
        return []


# ================================================================
# 🚀 AGENT LOOP
# ================================================================
def run_agent(command, user_input, model):

    spec = load_agent_spec(command)

    # ------------------------------------------------------------
    # ⚡ Deterministic router
    # ------------------------------------------------------------
    routing = route(user_input)

    if routing:
        trace = []
        step_counter = 0
        last_tool = None

        for step in routing["plan"]:
            step_counter += 1
            name = step["tool"]

            if name == last_tool:
                return error(f"Tool loop detected: {name}")

            last_tool = name

            result = run_tool(name, step["args"])

            trace.append({
                "event": "tool_call",
                "step": step_counter,
                "data": name,
                "meta": {
                    "input": step["args"],
                    "output": result
                }
            })

            if result.get("status") == "error":
                return error(f"Deterministic tool failed: {name}")

        return done("Task completed", {
            "mode": "deterministic",
            "agent": spec["name"],
            "agent_command": command,
            "steps": step_counter,
            "trace": trace
        })

    # ------------------------------------------------------------
    # 🤖 LLM PATH
    # ------------------------------------------------------------
    tools = load_tools()
    system_prompt = build_system_prompt(spec)

    messages = [
        {
            "role": "system",
            "content": system_prompt + "\n\nYou are a tool-using AI agent. Use tools when necessary to complete tasks."
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    trace = []
    step_counter = 0
    last_tool = None

    for _ in range(MAX_STEPS):

        response, err = call_llm(messages, model, tools)

        if err:
            return error(f"LLM error: {err}")

        msg = response["choices"][0]["message"]

        if msg.get("tool_calls"):

            messages.append(msg)

            for call in msg["tool_calls"]:
                step_counter += 1
                name = call["function"]["name"]

                if name == last_tool:
                    return error(f"Tool loop detected: {name}")

                last_tool = name

                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except Exception:
                    args = {}

                result = run_tool(name, args)

                trace.append({
                    "event": "tool_call",
                    "step": step_counter,
                    "data": name,
                    "meta": {
                        "input": args,
                        "output": result
                    }
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps({
                        "status": result.get("status"),
                        "data": result.get("data"),
                        "error": result.get("error")
                    })
                })

            continue

        content = (msg.get("content") or "").strip()

        if not content:
            return error("Empty model response")

        return done(content, {
            "model": model,
            "agent": spec["name"],
            "agent_command": command,
            "mode": "llm",
            "steps": step_counter,
            "trace": trace
        })

    return error("Max steps reached")


# ================================================================
# 🏁 ENTRYPOINT
# ================================================================
def main():
    args = sys.argv[1:]

    command = args[0] if len(args) > 0 else None
    user_input = args[1] if len(args) > 1 else ""

    model_override = None
    for a in args:
        if a.startswith("--model="):
            model_override = a.split("=", 1)[1]

    model = resolve_model(model_override)

    if not command:
        print(json.dumps(error("Missing command")))
        return

    result = run_agent(command, user_input, model)
    print(json.dumps(result))


if __name__ == "__main__":
    main()