#!/usr/bin/env python3
###################################################################
# read_file.py — Read file from workspace (MCP-compliant v3.0)
#
# Fixes:
# - Uses AI_WORKSPACE_DIR (session-isolated filesystem)
# - Strong path sandboxing
# - Safe byte-limited reads
###################################################################

import os

name = "read_file"
description = "Read a text file from the session workspace"

MAX_BYTES_DEFAULT = 65536  # 64KB safety limit

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Relative file path inside workspace"
        },
        "max_bytes": {
            "type": "integer",
            "description": "Maximum bytes to read",
            "default": MAX_BYTES_DEFAULT
        }
    },
    "required": ["path"]
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
    rel_path = input_data.get("path")
    max_bytes = int(input_data.get("max_bytes", MAX_BYTES_DEFAULT))

    # ---- Validate ----
    if not isinstance(rel_path, str) or not rel_path:
        return failure("Invalid or missing 'path'", "validation_error")

    if max_bytes <= 0:
        return failure("max_bytes must be > 0", "validation_error")

    full_path = resolve_path(rel_path)

    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    if not os.path.exists(full_path):
        return failure(f"File not found: {rel_path}", "not_found")

    if not os.path.isfile(full_path):
        return failure(f"Not a file: {rel_path}", "validation_error")

    try:
        # ---- Read safely with limit ----
        with open(full_path, "rb") as f:
            raw = f.read(max_bytes)

        content = raw.decode("utf-8", errors="replace")

        # Detect true truncation (file larger than max_bytes)
        file_size = os.path.getsize(full_path)
        truncated = file_size > max_bytes

        return success(
            {
                "path": rel_path,
                "absolute_path": full_path,
                "content": content,
                "bytes_read": len(raw),
                "truncated": truncated,
                "workspace": WORKSPACE_DIR
            },
            meta={"tool": "read_file"}
        )

    except Exception as e:
        return failure(str(e), "execution_error")