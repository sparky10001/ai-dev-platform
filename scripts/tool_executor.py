#!/usr/bin/env python3
###################################################################
# tool_executor.py — Python Tool Execution Engine (v3, production)
#
# Features:
# - Plugin auto-loading from /tools
# - Safe module import (no duplicate execution)
# - Structured JSON responses (contract-safe)
# - Tool metadata support
# - Built-in tool discovery (__list_tools)
###################################################################

import sys
import json
import os
import importlib.util
from datetime import datetime

SCRIPT_DIR = os.path.dirname(__file__)
TOOLS_DIR = os.path.join(SCRIPT_DIR, "tools")


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

        spec = importlib.util.spec_from_file_location(tool_name, filepath)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Do NOT crash — just skip broken tools
            print(json.dumps(error(f"Failed to load tool {tool_name}: {str(e)}")))
            continue

        # ---- Register executable ----
        if hasattr(module, "run") and callable(module.run):
            tools[tool_name] = module.run

        # ---- Register metadata ----
        metadata[tool_name] = {
            "name": getattr(module, "name", tool_name),
            "description": getattr(module, "description", ""),
            "input_schema": getattr(module, "input_schema", {}),
        }

    return tools, metadata


TOOLS, TOOL_METADATA = load_tools()


# ================================================================
# 🧰 BUILT-IN TOOLS
# ================================================================

def list_tools():
    return success(TOOL_METADATA)


# ================================================================
# 🚀 MAIN EXECUTION
# ================================================================

def main():
    try:
        if len(sys.argv) < 2:
            print(json.dumps(error("Missing tool name")))
            return

        tool_name = sys.argv[1]
        raw_input = sys.argv[2] if len(sys.argv) > 2 else "{}"

        # ---- Built-in commands ----
        if tool_name == "__list_tools":
            print(json.dumps(list_tools()))
            return

        # ---- Parse JSON input ----
        try:
            input_data = json.loads(raw_input)
        except json.JSONDecodeError:
            print(json.dumps(error("Invalid JSON input")))
            return

        # ---- Lookup tool ----
        tool = TOOLS.get(tool_name)

        if not tool:
            print(json.dumps(error(f"Unknown tool: {tool_name}")))
            return

        # ---- Execute tool safely ----
        try:
            result = tool(input_data)

            # Ensure result is JSON-serializable
            if isinstance(result, dict):
                print(json.dumps(result))
            else:
                print(json.dumps(success(result)))

        except Exception as e:
            print(json.dumps(error(f"Tool execution failed: {str(e)}")))

    except Exception as fatal:
        # Absolute safety net (never crash runtime)
        print(json.dumps({
            "status": "error",
            "output": f"Fatal executor error: {str(fatal)}",
            "meta": {
                "executor": "python",
                "timestamp": datetime.utcnow().isoformat()
            }
        }))


if __name__ == "__main__":
    main()