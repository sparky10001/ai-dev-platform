###################################################################
# write_file.py — File write tool (MCP-compliant v2.0)
###################################################################

import os

name = "write_file"
description = "Write a file within the workspace"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

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
# 🔐 PATH SAFETY
# ================================================================

def resolve_path(rel_path):
    full = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    if not full.startswith(BASE_DIR):
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

    if len(content.encode("utf-8")) > MAX_BYTES:
        return failure(
            f"Content exceeds max size ({MAX_BYTES} bytes)",
            "limit_exceeded"
        )

    full_path = resolve_path(rel_path)
    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    # ---- Overwrite protection ----
    if os.path.exists(full_path) and not overwrite:
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
                "bytes_written": len(content.encode("utf-8")),
                "overwritten": os.path.exists(full_path),
            },
            meta={"tool": "write_file"}
        )

    except Exception as e:
        return failure(f"Write failed: {str(e)}", "execution_error")