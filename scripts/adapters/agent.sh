#!/bin/bash
###################################################################
# agent.sh — Production Shim for agent.py
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_AGENT="${SCRIPT_DIR}/agent.py"

COMMAND="${1:-}"
INPUT="${2:-}"

# Shift so we can pass through future args safely
shift 2 || true

# ---------------------------------------------------------------
# 🧱 Safety Checks
# ---------------------------------------------------------------
if [ ! -f "$PY_AGENT" ]; then
  echo '{"status":"error","output":"agent.py not found","meta":{"adapter":"agent"}}'
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo '{"status":"error","output":"python3 not installed","meta":{"adapter":"agent"}}'
  exit 0
fi

# ---------------------------------------------------------------
# 🚀 Execute Agent (STRICT STDOUT ONLY)
# ---------------------------------------------------------------

TMP_ERR=$(mktemp)

OUTPUT=$(python3 "$PY_AGENT" "$COMMAND" "$INPUT" "$@" 2>"$TMP_ERR")
EXIT_CODE=$?

# ---------------------------------------------------------------
# ❌ Hard Failure Handling
# ---------------------------------------------------------------
if [ $EXIT_CODE -ne 0 ]; then
  ERR_MSG=$(cat "$TMP_ERR" | tail -n 5 | tr '\n' ' ')

  echo "$(jq -n \
    --arg msg "agent.py failed: $ERR_MSG" \
    '{status:"error", output:$msg, meta:{adapter:"agent"}}')"

  rm -f "$TMP_ERR"
  exit 0
fi

rm -f "$TMP_ERR"

# ---------------------------------------------------------------
# ✅ Validate JSON Output
# ---------------------------------------------------------------
if echo "$OUTPUT" | jq empty >/dev/null 2>&1; then
  echo "$OUTPUT"
else
  echo '{"status":"error","output":"Invalid JSON from agent.py","meta":{"adapter":"agent"}}'
fi
