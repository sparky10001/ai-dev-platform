#!/usr/bin/env python3
###################################################################
# tool_executor.py — Python Tool Execution Engine (v3.3 production)
#
# Features:
# - Plugin auto-loading from /tools
# - Backward compatible (legacy + MCP tool formats)
# - Strict normalized output contract
# - LiteLLM/OpenAI tool schema export
# - Safe module import (no duplicate execution)
# - Silent + safe execution (never crashes runtime)
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
# 🧾 HELPERS
# ================================================================

def debug(msg):
    if DEBUG:
        print(f"[tool_executor] {msg}", file=sys.stderr)


def safe_print(obj):
    try:
        print(json.dumps(obj))
    except Exception:
        print(json.dumps({
            "status": "error",
            "output": "Serialization failure",
            "meta": {"executor": "python"}
        }))


def timestamp():
    return datetime.utcnow().isoformat()


# ================================================================
# 🔄 TOOL SCHEMA CONVERSION (SAFE)
# ================================================================

def to_openai_tool_schema(tool_meta):
    """
    Converts internal tool metadata into OpenAI/LiteLLM format.
    Handles both proper JSON Schema and loose schemas.
    """
    raw_schema = tool_meta.get("input_schema", {})

    # ---- Case 1: Already valid JSON schema ----
    if isinstance(raw_schema, dict) and raw_schema.get("type") == "object":
        schema = raw_schema

    # ---- Case 2: Loose schema (your current tools) ----
    elif isinstance(raw_schema, dict):
        properties = {}
        required = []

        for key, val in raw_schema.items():
            properties[key] = {"type": "string"}  # safe fallback

            if isinstance(val, str) and "required" in val.lower():
                required.append(key)

        schema = {
            "type": "object",
            "properties": properties,
        }

        if required:
            schema["required"] = required

    # ---- Fallback ----
    else:
        schema = {
            "type": "object",
            "properties": {}
        }

    return {
        "type": "function",
        "function": {
            "name": tool_meta.get("name"),
            "description": tool_meta.get("description", ""),
            "parameters": schema
        }
    }


# ================================================================
# 🔌 TOOL LOADER
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

        # ---- Register run() ----
        if hasattr(module, "run") and callable(module.run):
            tools[tool_name] = module.run
        else:
            debug(f"Tool {tool_name} missing run()")

        # ---- Metadata ----
        metadata[tool_name] = {
            "name": getattr(module, "name", tool_name),
            "description": getattr(module, "description", ""),
            "input_schema": getattr(module, "input_schema", {}),
        }

    return tools, metadata


TOOLS, TOOL_METADATA = load_tools()


# ================================================================
# 🔄 RESULT NORMALIZATION (CRITICAL)
# ================================================================

def normalize_result(result):
    """
    Accepts:
    - Legacy: {status: "done", output: ...}
    - MCP:    {status: "success", data: ...}

    Returns STRICT:
    {
      status: "success" | "error",
      data: ...,
      error: {message, type} | None,
      meta: {}
    }
    """

    # ---- Non-dict fallback ----
    if not isinstance(result, dict):
        return {
            "status": "success",
            "data": {"value": str(result)},
            "error": None,
            "meta": {}
        }

    status = result.get("status")

    # ============================================================
    # 🔁 LEGACY FORMAT SUPPORT
    # ============================================================
    if status == "done":
        return {
            "status": "success",
            "data": result.get("output"),
            "error": None,
            "meta": result.get("meta", {})
        }

    if status == "error" and "output" in result:
        return {
            "status": "error",
            "data": None,
            "error": {
                "message": result.get("output"),
                "type": result.get("type", "tool_error")
            },
            "meta": result.get("meta", {})
        }

    # ============================================================
    # ✅ MCP FORMAT
    # ============================================================
    if status == "success":
        return {
            "status": "success",
            "data": result.get("data", {}),
            "error": None,
            "meta": result.get("meta", {})
        }

    if status == "error":
        return {
            "status": "error",
            "data": None,
            "error": result.get("error") or {
                "message": "Unknown error",
                "type": "unknown"
            },
            "meta": result.get("meta", {})
        }

    # ---- Unknown contract ----
    return {
        "status": "error",
        "data": None,
        "error": {
            "message": "Invalid tool response",
            "type": "contract_error"
        },
        "meta": {}
    }


# ================================================================
# 🧰 BUILT-IN COMMANDS
# ================================================================

def handle_list_tools():
    safe_print({
        "status": "done",
        "tools": TOOL_METADATA
    })


def handle_list_tools_openai():
    tools = []

    for tool_name, meta in TOOL_METADATA.items():
        try:
            tools.append(to_openai_tool_schema(meta))
        except Exception as e:
            debug(f"Schema conversion failed for {tool_name}: {e}")

    safe_print({
        "status": "done",
        "tools": tools
    })


# ================================================================
# 🚀 MAIN
# ================================================================

def main():
    try:
        if len(sys.argv) < 2:
            safe_print({
                "status": "error",
                "output": "Missing tool name"
            })
            return

        cmd = sys.argv[1]

        # ---- Built-ins ----
        if cmd == "--list-tools":
            handle_list_tools()
            return

        if cmd == "--list-tools-openai":
            handle_list_tools_openai()
            return

        tool_name = cmd
        raw_input = sys.argv[2] if len(sys.argv) > 2 else "{}"

        # ---- Parse input ----
        try:
            input_data = json.loads(raw_input)
        except json.JSONDecodeError:
            safe_print({
                "status": "error",
                "output": "Invalid JSON input"
            })
            return

        tool = TOOLS.get(tool_name)

        if not tool:
            safe_print({
                "status": "error",
                "output": f"Unknown tool: {tool_name}"
            })
            return

        # ---- Execute ----
        try:
            result = tool(input_data)
            normalized = normalize_result(result)
            safe_print(normalized)

        except Exception as e:
            safe_print({
                "status": "error",
                "output": f"Tool execution failed: {str(e)}"
            })

    except Exception as fatal:
        safe_print({
            "status": "error",
            "output": f"Fatal executor error: {str(fatal)}",
            "meta": {
                "executor": "python",
                "timestamp": timestamp()
            }
        })


if __name__ == "__main__":
    main()