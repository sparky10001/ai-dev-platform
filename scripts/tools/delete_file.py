#!/usr/bin/env python3
###################################################################
# delete_file.py — Safe file/directory deletion (MCP-compliant v1.0)
###################################################################

import os
import shutil

name = "delete_file"
description = "Delete a file or directory within the workspace"

# ================================================================
# 📁 WORKSPACE ROOT (safe boundary)
# ================================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Optional dry-run (shared convention with log_manager)
DRY_RUN = os.getenv("AI_LOG_DRY_RUN", "0") == "1"

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Relative path inside workspace"
        },
        "recursive": {
            "type": "boolean",
            "description": "Delete directories recursively",
            "default": False
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
# 🔐 PATH SAFETY
# ================================================================

def resolve_path(rel_path):
    if not isinstance(rel_path, str):
        return None

    full_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    base_real = os.path.realpath(BASE_DIR)
    target_real = os.path.realpath(full_path)

    if not target_real.startswith(base_real + os.sep):
        return None

    return full_path

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    rel_path = input_data.get("path")
    recursive = input_data.get("recursive", False)

    if not isinstance(rel_path, str):
        return failure("Invalid 'path' (must be string)", "validation_error")

    if not isinstance(recursive, bool):
        return failure("Invalid 'recursive' (must be boolean)", "validation_error")

    full_path = resolve_path(rel_path)

    if not full_path:
        return failure("Access denied (path outside workspace)", "security_error")

    if not os.path.exists(full_path):
        return failure(f"Path not found: {rel_path}", "not_found")

    try:
        # --------------------------------------------------------
        # 📄 FILE
        # --------------------------------------------------------
        if os.path.isfile(full_path) or os.path.islink(full_path):
            if DRY_RUN:
                return success(
                    {
                        "path": rel_path,
                        "deleted": False,
                        "type": "file",
                        "dry_run": True
                    },
                    meta={"tool": "delete_file"}
                )

            os.remove(full_path)

            return success(
                {
                    "path": rel_path,
                    "deleted": True,
                    "type": "file"
                },
                meta={"tool": "delete_file"}
            )

        # --------------------------------------------------------
        # 📁 DIRECTORY
        # --------------------------------------------------------
        if os.path.isdir(full_path):
            if not recursive:
                # Only allow delete if empty
                if os.listdir(full_path):
                    return failure(
                        "Directory not empty (use recursive=true)",
                        "validation_error"
                    )

                if DRY_RUN:
                    return success(
                        {
                            "path": rel_path,
                            "deleted": False,
                            "type": "directory",
                            "dry_run": True
                        },
                        meta={"tool": "delete_file"}
                    )

                os.rmdir(full_path)

                return success(
                    {
                        "path": rel_path,
                        "deleted": True,
                        "type": "directory"
                    },
                    meta={"tool": "delete_file"}
                )

            # Recursive delete
            if DRY_RUN:
                return success(
                    {
                        "path": rel_path,
                        "deleted": False,
                        "type": "directory",
                        "recursive": True,
                        "dry_run": True
                    },
                    meta={"tool": "delete_file"}
                )

            shutil.rmtree(full_path)

            return success(
                {
                    "path": rel_path,
                    "deleted": True,
                    "type": "directory",
                    "recursive": True
                },
                meta={"tool": "delete_file"}
            )

        return failure("Unsupported file type", "execution_error")

    except PermissionError:
        return failure("Permission denied", "permission_error")

    except Exception as e:
        return failure(str(e), "execution_error")