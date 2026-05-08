#!/usr/bin/env bash
###################################################################
# agent.sh — Production Shim for agent.py (v9 FIXED PATHS)
###################################################################

set -euo pipefail

# ---------------------------------------------------------------
# 📁 Paths
# ---------------------------------------------------------------
ADAPTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "${ADAPTER_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${SCRIPTS_DIR}/.." && pwd)"

PY_AGENT="${SCRIPTS_DIR}/agent.py"
TOOL_EXECUTOR="${SCRIPTS_DIR}/tool_executor.py"

COMMAND="${1:-}"
INPUT="${2:-}"

shift 2 || true

# ---------------------------------------------------------------
# 🧱 Safety Checks
# ---------------------------------------------------------------
if [ ! -f "$PY_AGENT" ]; then
  echo '{"status":"error","output":"agent.py not found","meta":{"adapter":"agent"}}'
  exit 0
fi

if [ ! -f "$TOOL_EXECUTOR" ]; then
  echo '{"status":"error","output":"tool_executor missing","meta":{"adapter":"agent"}}'
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo '{"status":"error","output":"python3 not installed","meta":{"adapter":"agent"}}'
  exit 0
fi

# ---------------------------------------------------------------
# 🧠 Validate Tool Registry
# ---------------------------------------------------------------
RAW_TOOLS=$(python3 "$TOOL_EXECUTOR" --list-tools 2>/dev/null || echo '{}')

TOOL_COUNT=$(echo "$RAW_TOOLS" | jq '.tools | length' 2>/dev/null || echo 0)

if [ "$TOOL_COUNT" -eq 0 ]; then
  echo '{"status":"error","output":"No tools registered","meta":{"adapter":"agent"}}'
  exit 0
fi

# ---------------------------------------------------------------
# 🚀 Execute Agent
# ---------------------------------------------------------------
TMP_ERR=$(mktemp)

OUTPUT=$(python3 "$PY_AGENT" \
  "$COMMAND" \
  "$INPUT" \
  "$@" 2>"$TMP_ERR")

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  ERR_MSG=$(tail -n 20 "$TMP_ERR" | tr '\n' ' ')

  echo "$(jq -n \
    --arg msg "$ERR_MSG" \
    '{status:"error",output:$msg,meta:{adapter:"agent"}}')"

  rm -f "$TMP_ERR"
  exit 0
fi

rm -f "$TMP_ERR"

# ---------------------------------------------------------------
# 🔒 Validate JSON
# ---------------------------------------------------------------
if ! echo "$OUTPUT" | jq empty >/dev/null 2>&1; then
  echo '{"status":"error","output":"Invalid JSON from agent.py","meta":{"adapter":"agent"}}'
  exit 0
fi

# ---------------------------------------------------------------
# ✅ Success
# ---------------------------------------------------------------
echo "$OUTPUT"