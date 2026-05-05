#!/usr/bin/env python3
###################################################################
# write_file.py — File write tool (MCP-compliant v3.0)
#
# Fixes:
# - Uses AI_WORKSPACE_DIR (session-isolated filesystem)
# - Strong path sandboxing
# - Correct overwrite detection
###################################################################

import os

name = "write_file"
description = "Write a file within the session workspace"

MAX_BYTES = 262144  # 256KB safety limit

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "File path (relative to workspace)"
        },
        "content": {
            "type": "string",
            "description": "File content"
        },
        "overwrite": {
            "type": "boolean",
            "description": "Allow overwrite if file exists",
            "default": True
        }
    },
    "required": ["path", "content"]
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
    full = os.path.abspath(os.path.join(WORKSPACE_DIR, rel_path))

    # Prevent escaping workspace (../ attacks)
    if not full.startswith(os.path.abspath(WORKSPACE_DIR)):
        return None

    return full

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    rel_path = input_data.get("path")
    content = input_data.get("content")
    overwrite = bool(input_data.get("overwrite", True))

    # ---- Validate ----
    if not isinstance(rel_path, str) or not rel_path:
        return failure("Invalid or missing 'path'", "validation_error")

    if not isinstance(content, str):
        return failure("Invalid or missing 'content'", "validation_error")

    encoded = content.encode("utf-8")

    if len(encoded) > MAX_BYTES:
        return failure(
            f"Content exceeds max size ({MAX_BYTES} bytes)",
            "limit_exceeded"
        )

    full_path = resolve_path(rel_path)
    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    # ---- Overwrite detection BEFORE write ----
    existed_before = os.path.exists(full_path)

    if existed_before and not overwrite:
        return failure(
            f"File exists and overwrite disabled: {rel_path}",
            "conflict"
        )

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return success(
            {
                "path": rel_path,
                "absolute_path": full_path,
                "bytes_written": len(encoded),
                "overwritten": existed_before,
                "workspace": WORKSPACE_DIR
            },
            meta={"tool": "write_file"}
        )

    except Exception as e:
        return failure(f"Write failed: {str(e)}", "execution_error")