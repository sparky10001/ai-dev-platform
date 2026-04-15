#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock AI Adapter (v4 production)
#
# Purpose:
# - Deterministic offline testing
# - Loop + tool simulation
# - Proper tool lifecycle handling
# - CI-safe behavior
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Adapter identity ----
ADAPTER_NAME="mock"

# ---- Load shared base ----
source "${SCRIPT_DIR}/_base.sh"

# ---- Validate ----
if [ -z "$COMMAND" ]; then
  build_response "error" "Missing command" "invalid_request"
  adapter_exit
fi

# ---- Normalize input ----
LOWER_INPUT=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]')

# ================================================================
# 🧠 TOOL RESULT HANDLING (CRITICAL FIX)
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool')
  TOOL_RESULT=$(echo "$INPUT" | jq -r '.result')

  build_response "done" "[MOCK] Tool '$TOOL_NAME' completed:\n$TOOL_RESULT" "" \
    '{"mode":"tool_complete"}'

  adapter_exit
fi

# ================================================================
# 🧠 BEHAVIOR SIMULATION ENGINE
# ================================================================

case "$COMMAND" in

# ---------------------------------------------------------------
# 🏃 RUN
# ---------------------------------------------------------------
run)

  # 🔁 Loop simulation
  if [[ "$LOWER_INPUT" == *"loop"* ]]; then
    build_response "continue" "[MOCK] Looping..." "" \
      '{"mode":"loop"}'
    adapter_exit
  fi

  # 🛠️ Tool call simulation
  if [[ "$LOWER_INPUT" == *"tool"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Calling mock tool"
    adapter_exit
  fi

  # ✅ Normal execution
  build_response "done" "[MOCK RUN] Executing: $INPUT"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 📘 EXPLAIN
# ---------------------------------------------------------------
explain)
  build_response "done" "[MOCK EXPLAIN] $INPUT"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 🛠️ FIX
# ---------------------------------------------------------------
fix)
  build_response "done" "[MOCK FIX] $INPUT"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# ♻️ REFACTOR
# ---------------------------------------------------------------
refactor)
  build_response "done" "[MOCK REFACTOR] $INPUT"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 🔎 QUERY
# ---------------------------------------------------------------
query)
  build_response "done" "[MOCK QUERY] $INPUT"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# ❌ UNKNOWN
# ---------------------------------------------------------------
*)
  build_response "error" "[MOCK ERROR] Unknown command: $COMMAND" "invalid_request"
  adapter_exit
  ;;
esac