#!/usr/bin/env python3
###################################################################
# tool_executor.py — Python Tool Execution Engine (v3.1 production)
#
# Features:
# - Plugin auto-loading from /tools
# - Safe module import (no duplicate execution)
# - Structured JSON responses (contract-safe)
# - Tool metadata support
# - Built-in tool discovery (--list-tools)
# - Output normalization (string/dict safe)
# - Silent failures (no stdout pollution)
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
# 🏗️ RESPONSE HELPERS
# ================================================================

def build_response(status, output, extra_meta=None):
    return {
        "status": status,
        "output": output,
        "meta": {
            "executor": "python",
            "timestamp": datetime.utcnow().isoformat(),
            **(extra_meta or {}),
        },
    }


def success(output, meta=None):
    return build_response("done", output, meta)


def error(message, meta=None):
    return build_response("error", message, meta)


def safe_print(obj):
    """Never crash on serialization"""
    try:
        print(json.dumps(obj))
    except Exception:
        print(json.dumps({
            "status": "error",
            "output": "Serialization failure",
            "meta": {"executor": "python"}
        }))


def debug(msg):
    if DEBUG:
        print(f"[tool_executor] {msg}", file=sys.stderr)


# ================================================================
# 🔌 PLUGIN LOADER (SAFE + CACHED)
# ================================================================

def load_tools():
    tools = {}
    metadata = {}

    if not os.path.isdir(TOOLS_DIR):
        return tools, metadata

    for filename in os.listdir(TOOLS_DIR):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        tool_name = filename[:-3]
        filepath = os.path.join(TOOLS_DIR, filename)

        try:
            spec = importlib.util.spec_from_file_location(tool_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            debug(f"Failed to load tool {tool_name}: {e}")
            continue

        # ---- Register executable ----
        if hasattr(module, "run") and callable(module.run):
            tools[tool_name] = module.run
        else:
            debug(f"Tool {tool_name} missing run()")

        # ---- Register metadata ----
        metadata[tool_name] = {
            "name": getattr(module, "name", tool_name),
            "description": getattr(module, "description", ""),
            "input_schema": getattr(module, "input_schema", {}),
        }

    return tools, metadata


TOOLS, TOOL_METADATA = load_tools()


# ================================================================
# 🧰 BUILT-IN COMMANDS
# ================================================================

def handle_list_tools():
    safe_print({
        "status": "done",
        "tools": TOOL_METADATA
    })


# ================================================================
# 🔄 RESULT NORMALIZATION
# ================================================================

def normalize_result(result):
    """
    Ensures all tool outputs conform to contract:
    - dict → pass through (must include status)
    - string → wrap as success
    - anything else → stringify safely
    """
    if isinstance(result, dict):
        if "status" not in result:
            return success(result)
        return result

    if isinstance(result, str):
        return success(result)

    return success(str(result))


# ================================================================
# 🚀 MAIN EXECUTION
# ================================================================

def main():
    try:
        if len(sys.argv) < 2:
            safe_print(error("Missing tool name"))
            return

        # ---- Built-in commands FIRST ----
        if sys.argv[1] == "--list-tools":
            handle_list_tools()
            return

        tool_name = sys.argv[1]
        raw_input = sys.argv[2] if len(sys.argv) > 2 else "{}"

        # ---- Parse JSON input ----
        try:
            input_data = json.loads(raw_input)
        except json.JSONDecodeError:
            safe_print(error("Invalid JSON input"))
            return

        # ---- Lookup tool ----
        tool = TOOLS.get(tool_name)

        if not tool:
            safe_print(error(f"Unknown tool: {tool_name}"))
            return

        # ---- Execute tool safely ----
        try:
            result = tool(input_data)
            normalized = normalize_result(result)
            safe_print(normalized)

        except Exception as e:
            safe_print(error(f"Tool execution failed: {str(e)}"))

    except Exception as fatal:
        # Absolute safety net (never break runtime)
        safe_print({
            "status": "error",
            "output": f"Fatal executor error: {str(fatal)}",
            "meta": {
                "executor": "python",
                "timestamp": datetime.utcnow().isoformat()
            }
        })


if __name__ == "__main__":
    main()