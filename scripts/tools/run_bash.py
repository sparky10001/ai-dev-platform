###################################################################
# run_bash.py — Shell execution tool (MCP-compliant v2.0)
###################################################################

import os
import subprocess
import shlex

name = "run_bash"
description = "Execute a shell command within the workspace (restricted)"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

MAX_OUTPUT_BYTES = 65536  # 64KB

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Shell command to execute"
        },
        "timeout": {
            "type": "integer",
            "description": "Max execution time in seconds",
            "default": 30
        },
        "cwd": {
            "type": "string",
            "description": "Working directory (relative to workspace)"
        }
    },
    "required": ["command"]
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
# 🔐 SAFETY
# ================================================================

BLOCKED_SUBSTRINGS = [
    "rm -rf /",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "shutdown",
    "reboot",
]

def is_blocked(command):
    cmd = command.lower()
    return any(b in cmd for b in BLOCKED_SUBSTRINGS)

def resolve_cwd(rel_path):
    if not rel_path:
        return BASE_DIR

    full = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    if not full.startswith(BASE_DIR):
        return None
    if not os.path.isdir(full):
        return None
    return full

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    command = input_data.get("command")
    timeout = int(input_data.get("timeout", 30))
    rel_cwd = input_data.get("cwd", "")

    # ---- Validate ----
    if not isinstance(command, str) or not command.strip():
        return failure("Invalid or missing 'command'", "validation_error")

    if is_blocked(command):
        return failure("Command blocked for safety", "security_error")

    work_dir = resolve_cwd(rel_cwd)
    if not work_dir:
        return failure("Invalid or unsafe working directory", "security_error")

    try:
        # ⚠️ safer than raw shell=True parsing
        process = subprocess.run(
            command,
            shell=True,  # keeping for flexibility, but controlled
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        # ---- Truncate output ----
        combined = (stdout + stderr)[:MAX_OUTPUT_BYTES]

        return success(
            {
                "command": command,
                "cwd": rel_cwd or ".",
                "exit_code": process.returncode,
                "stdout": stdout[:MAX_OUTPUT_BYTES],
                "stderr": stderr[:MAX_OUTPUT_BYTES],
                "output": combined.strip() or "(no output)",
                "truncated": len(stdout + stderr) > MAX_OUTPUT_BYTES,
                "success": process.returncode == 0
            },
            meta={"tool": "run_bash"}
        )

    except subprocess.TimeoutExpired:
        return failure(
            f"Command timed out after {timeout}s",
            "timeout",
            meta={"command": command}
        )

    except Exception as e:
        return failure(f"Execution error: {str(e)}", "execution_error")