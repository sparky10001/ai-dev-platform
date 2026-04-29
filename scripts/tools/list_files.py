###################################################################
# list_files.py — List files in workspace (MCP-compliant v2.0)
###################################################################

import os

name = "list_files"
description = "List files and directories within a workspace directory"

# Workspace root (safe boundary)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ================================================================
# 🧾 INPUT SCHEMA (JSON Schema for tool calling)
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
# 🔐 PATH RESOLUTION
# ================================================================

def resolve_path(rel_path):
    full_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    if not full_path.startswith(BASE_DIR):
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

        # ✅ Deterministic output (important for LLMs)
        entries.sort(key=lambda x: (x["type"], x["name"]))

        return success(
            {
                "path": rel_path,
                "entries": entries,
                "count": len(entries)
            },
            meta={"tool": "list_files"}
        )

    except Exception as e:
        return failure(str(e), "execution_error")