###################################################################
# run_bash.py — Shell command execution tool (v1.2 production)
#
# Safety features:
# - Workspace-scoped execution (CWD = BASE_DIR)
# - Configurable timeout
# - Blocked command list
# - Stdout + stderr capture
# - Exit code in response
###################################################################

import os
import subprocess

name = "run_bash"
description = "Execute a shell command safely within the workspace"
input_schema = {
    "command": "string (required) — shell command to execute",
    "timeout": "int (optional, default 30) — max seconds to wait",
    "cwd": "string (optional) — subdirectory to run in (relative to workspace)"
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ---- Blocked commands (safety layer) ----
BLOCKED = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",   # fork bomb
    "sudo rm",
    "> /dev/sda",
]

def is_blocked(command):
    cmd_lower = command.lower().strip()
    return any(blocked in cmd_lower for blocked in BLOCKED)


def run(input_data):
    command = input_data.get("command")
    timeout = input_data.get("timeout", 30)
    rel_cwd = input_data.get("cwd", "")

    # ---- Validate ----
    if not command:
        return {"status": "error", "output": "Missing 'command'"}

    if not isinstance(command, str):
        return {"status": "error", "output": "'command' must be a string"}

    if is_blocked(command):
        return {"status": "error", "output": f"Blocked command: {command}"}

    # ---- Resolve working directory ----
    if rel_cwd:
        work_dir = os.path.abspath(os.path.join(BASE_DIR, rel_cwd))
        if not work_dir.startswith(BASE_DIR):
            return {"status": "error", "output": "Access denied (cwd outside workspace)"}
        if not os.path.isdir(work_dir):
            return {"status": "error", "output": f"Directory not found: {rel_cwd}"}
    else:
        work_dir = BASE_DIR

    # ---- Execute ----
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=int(timeout),
            cwd=work_dir
        )

        # Combine stdout + stderr
        output = result.stdout
        if result.stderr:
            output = output + result.stderr if output else result.stderr

        output = output.strip() if output else ""

        return {
            "status": "done",
            "output": output or "(no output)",
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "output": f"Command timed out after {timeout}s: {command}"
        }

    except Exception as e:
        return {
            "status": "error",
            "output": f"Execution error: {str(e)}"
        }
