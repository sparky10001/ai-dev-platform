#!/bin/bash
###################################################################
# tool_executor.sh — Stable tool execution interface (wrapper)
#
# Delegates execution to Python implementation
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY_EXECUTOR="${SCRIPT_DIR}/tool_executor.py"

if [ ! -f "$PY_EXECUTOR" ]; then
    echo '{"status":"error","output":"Python tool executor not found","meta":{"adapter":"tool_executor"}}'
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo '{"status":"error","output":"python3 not installed","meta":{"adapter":"tool_executor"}}'
    exit 0
fi

python3 "$PY_EXECUTOR" "$@"