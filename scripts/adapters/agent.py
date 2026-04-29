#!/usr/bin/env python3
###################################################################
# agent.py — Production LiteLLM Agent (v3.0)
#
# Improvements:
# - Correct model resolution (no env leakage)
# - Resolved provider visibility (no silent fallback)
# - Stable OpenAI tool schema
# - Deterministic retry + backoff
# - Tool loop protection
# - Strict MCP-style output
###################################################################

import os
import sys
import json
import time
import requests
import subprocess

# ================================================================
# ⚙️ CONFIG
# ================================================================
BASE_URL = os.getenv("LITELLM_BASE_URL", "http://litellm:4000/v1")
MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "ai-dev-platform")

DEFAULT_MODEL = "balanced"
MAX_STEPS = int(os.getenv("AI_MAX_STEPS", "4"))
TIMEOUT = int(os.getenv("AI_TIMEOUT", "60"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_EXECUTOR = os.path.join(SCRIPT_DIR, "tool_executor.py")

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
# 🌐 LLM CALL (RETRY SAFE)
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
                last_err = "Invalid LLM response (no choices)"
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
            return {
                "status": "error",
                "error": {
                    "message": proc.stderr.strip(),
                    "type": "execution_error"
                }
            }

        return json.loads(proc.stdout)

    except Exception as e:
        return {
            "status": "error",
            "error": {
                "message": str(e),
                "type": "exception"
            }
        }

# ================================================================
# 🧰 TOOL DISCOVERY (FIXED CONTRACT)
# ================================================================
def load_tools():
    try:
        proc = subprocess.run(
            ["python3", TOOL_EXECUTOR, "--list-tools"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if proc.returncode != 0:
            return []

        data = json.loads(proc.stdout)

        tools = []

        for t in data.get("tools", {}).values():
            tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            })

        return tools

    except Exception:
        return []

# ================================================================
# 🚀 AGENT LOOP
# ================================================================
def run_agent(command, user_input, model):
    tools = load_tools()

    trace = []
    step_counter = 0
    last_tool = None

    messages = [
        {
            "role": "system",
            "content": (
                "You are a tool-using AI agent.\n"
                "If a tool can complete the task, you MUST call it.\n"
                "Do not explain tools.\n"
                "Return short confirmations when done."
            )
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    resolved_model = "unknown"

    for _ in range(MAX_STEPS):

        response, err = call_llm(messages, model, tools)

        if err:
            return error(f"LLM error: {err}")

        resolved_model = response.get("model", "unknown")

        msg = response["choices"][0]["message"]

        # ========================================================
        # 🔧 TOOL CALLS
        # ========================================================
        if msg.get("tool_calls"):

            messages.append(msg)

            for call in msg["tool_calls"]:
                step_counter += 1

                name = call["function"]["name"]

                # 🚫 prevent infinite loops
                if name == last_tool:
                    return error("Tool loop detected")

                last_tool = name

                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except Exception:
                    args = {}

                result = run_tool(name, args)

                trace.append({
                    "event": "tool_call",
                    "step": step_counter,
                    "tool": name,
                    "input": args,
                    "output": result
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result)
                })

            continue

        # ========================================================
        # ✅ FINAL OUTPUT
        # ========================================================
        content = (msg.get("content") or "").strip()

        if not content:
            return error("Empty model response")

        return done(content, {
            "model": model,
            "resolved_model": resolved_model,
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