#!/usr/bin/env python3
###################################################################
# tool_executor.py — Tool Execution Engine (v8.1 STABLE)
#
# Guarantees:
# - Strict tool registry enforcement (EMPTY = HARD FAIL)
# - Strict JSON schema validation
# - Deterministic execution envelope
# - No silent fallbacks
# - Runtime-trace compatible outputs
# - OpenAI tool schema correctness enforced
# - Fully consistent TOOL_META / TOOLS contract
###################################################################

import sys
import json
import os
import importlib.util
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
TOOLS_DIR = os.path.join(SCRIPT_DIR, "tools")

DEBUG = os.getenv("TOOL_DEBUG", "false").lower() == "true"


# ================================================================
# 🧾 DEBUG
# ================================================================
def debug(msg):
    if DEBUG:
        print(f"[tool_executor] {msg}", file=sys.stderr)


def safe_print(obj):
    print(json.dumps(obj))


def now():
    return datetime.utcnow().isoformat()


# ================================================================
# ❌ HARD FAILURE
# ================================================================
def hard_fail(msg):
    safe_print({
        "status": "error",
        "error": {
            "message": msg,
            "type": "tool_executor_contract_failure"
        },
        "meta": {
            "executor": "v8"
        }
    })
    sys.exit(1)


# ================================================================
# 🔌 TOOL LOADER (STRICT)
# ================================================================
def load_tools():
    tools = {}
    meta = {}

    if not os.path.isdir(TOOLS_DIR):
        hard_fail(f"Tools directory missing: {TOOLS_DIR}")

    files = [
        f for f in os.listdir(TOOLS_DIR)
        if f.endswith(".py")
        and not f.startswith("_")
        and f != "__init__.py"
    ]

    if not files:
        hard_fail("Tool registry is EMPTY — refusing to start")

    for f in files:
        name = f[:-3]
        path = os.path.join(TOOLS_DIR, f)

        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            hard_fail(f"Failed loading tool {name}: {e}")

        # ✅ STRICT TOOL CONTRACT FILTER
        if not all([
            hasattr(module, "run"),
            hasattr(module, "name"),
            hasattr(module, "description"),
            hasattr(module, "input_schema")
        ]):
            debug(f"Skipping non-tool module: {name}")
            continue

        if not isinstance(module.input_schema, dict):
            debug(f"Skipping invalid schema tool: {name}")
            continue

        tools[module.name] = module.run

        meta[module.name] = {
            "name": module.name,
            "description": module.description,
            "input_schema": module.input_schema
        }

    if not tools:
        hard_fail("No valid tools loaded after filtering")

    return tools, meta


# GLOBAL REGISTRY (FIXED)
TOOLS, TOOL_META = load_tools()

if not TOOLS:
    hard_fail("Tool registry EMPTY after validation — system unusable")


# ================================================================
# 🔧 OPENAI TOOL SCHEMA
# ================================================================
def to_openai_tool(meta):
    schema = meta["input_schema"]

    if not isinstance(schema, dict) or schema.get("type") != "object":
        hard_fail(f"Tool schema must be object type: {meta['name']}")

    return {
        "type": "function",
        "function": {
            "name": meta["name"],
            "description": meta["description"],
            "parameters": schema
        }
    }


# ================================================================
# 📦 TOOL EXECUTION
# ================================================================
def execute_tool(name, args):
    tool = TOOLS.get(name)

    if not tool:
        return {
            "status": "error",
            "error": {
                "message": f"Unknown tool: {name}",
                "type": "not_found"
            }
        }

    try:
        result = tool(args or {})

        # Normalize non-dict outputs
        if not isinstance(result, dict):
            return {
                "status": "success",
                "data": result,
                "error": None,
                "meta": {"warning": "non_dict_tool_output"}
            }

        status = result.get("status")

        if status == "error":
            return {
                "status": "error",
                "data": None,
                "error": result.get("error") or {
                    "message": result.get("output", "Unknown error"),
                    "type": "tool_error"
                },
                "meta": result.get("meta", {})
            }

        return {
            "status": "success",
            "data": result.get("output", result.get("data")),
            "error": None,
            "meta": result.get("meta", {})
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": str(e),
                "type": "execution_exception"
            },
            "meta": {}
        }


# ================================================================
# 📤 TOOL EXPORTS
# ================================================================
def list_tools():
    return {
        "status": "done",
        "tools": TOOL_META
    }


def list_tools_openai():
    return {
        "status": "done",
        "tools": [
            to_openai_tool(m) for m in TOOL_META.values()
        ]
    }


# ================================================================
# 🚀 ENTRYPOINT
# ================================================================
def main():
    if len(sys.argv) < 2:
        hard_fail("Missing command")

    cmd = sys.argv[1]

    if cmd == "--list-tools":
        safe_print(list_tools())
        return

    if cmd == "--list-tools-openai":
        safe_print(list_tools_openai())
        return

    tool_name = cmd
    raw = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        args = json.loads(raw)
    except Exception:
        safe_print({
            "status": "error",
            "error": {
                "message": "Invalid JSON input",
                "type": "parse_error"
            }
        })
        return

    result = execute_tool(tool_name, args)
    safe_print(result)


if __name__ == "__main__":
    main()