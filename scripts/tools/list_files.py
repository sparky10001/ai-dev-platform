#!/usr/bin/env python3
###################################################################
# list_files.py — List files in workspace (MCP-compliant v3.0)
#
# Fixes:
# - Uses AI_WORKSPACE_DIR (session-isolated filesystem)
# - Strong path sandboxing
# - Deterministic output
###################################################################

import os

name = "list_files"
description = "List files and directories within the session workspace"

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Relative path inside workspace",
            "default": ""
        }
    }
}

# ================================================================
# 🧱 RESPONSE HELPERS
# ================================================================

def success(data, meta=None):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "meta": meta or {}
    }

def failure(message, error_type="tool_error", meta=None):
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
# 🔐 WORKSPACE RESOLUTION (CRITICAL)
# ================================================================

WORKSPACE_DIR = os.getenv("AI_WORKSPACE_DIR") or os.getcwd()

def resolve_path(rel_path: str):
    full_path = os.path.abspath(os.path.join(WORKSPACE_DIR, rel_path))

    # Prevent escaping workspace
    if not full_path.startswith(os.path.abspath(WORKSPACE_DIR)):
        return None

    return full_path

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    rel_path = input_data.get("path", "")

    if not isinstance(rel_path, str):
        return failure("Invalid 'path' (must be string)", "validation_error")

    full_path = resolve_path(rel_path)

    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    if not os.path.exists(full_path):
        return failure(f"Path not found: {rel_path}", "not_found")

    if not os.path.isdir(full_path):
        return failure(f"Not a directory: {rel_path}", "validation_error")

    try:
        entries = []

        for name_ in os.listdir(full_path):
            entry_path = os.path.join(full_path, name_)

            entries.append({
                "name": name_,
                "type": "directory" if os.path.isdir(entry_path) else "file"
            })

        # ✅ Deterministic output (important for LLM + evals)
        entries.sort(key=lambda x: (x["type"], x["name"]))

        return success(
            {
                "path": rel_path,
                "absolute_path": full_path,
                "entries": entries,
                "count": len(entries),
                "workspace": WORKSPACE_DIR
            },
            meta={"tool": "list_files"}
        )

    except Exception as e:
        return failure(str(e), "execution_error")