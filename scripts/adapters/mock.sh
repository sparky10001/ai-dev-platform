#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock AI Adapter (v5.1 production)
#
# Fully aligned with openai/http-agent pattern
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- Adapter identity ----
ADAPTER_NAME="mock"

# ---- Load shared base ----
source "${SCRIPT_DIR}/_base.sh"

# ---- Normalize input safely ----
INPUT="${INPUT:-}"
LOWER_INPUT=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]' 2>/dev/null || echo "")

# ================================================================
# 🧠 TOOL RESULT HANDLING (MUST COME FIRST)
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
  TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

  build_response "done" "[MOCK] Tool '$TOOL_NAME' completed:\n$TOOL_RESULT" "" \
    '{"mode":"tool_complete"}'

  adapter_exit
fi

# ---- Validate ----
if [ -z "$COMMAND" ]; then
  build_response "error" "Missing command" "invalid_request"
  adapter_exit
fi

# ================================================================
# 🔌 TOOL-AWARE PROMPT SIMULATION (PARITY FEATURE)
# ================================================================
TOOL_CONTEXT=""

if command -v python3 >/dev/null 2>&1 && [ -f "${SCRIPT_DIR}/../tool_executor.py" ]; then
    TOOL_METADATA=$(python3 "${SCRIPT_DIR}/../tool_executor.py" --list-tools 2>/dev/null || echo "[]")

    TOOL_CONTEXT="\n\nAvailable tools:\n${TOOL_METADATA}\n\nUse tools when appropriate."
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
    build_response "continue" "[MOCK] Looping..." "" '{"mode":"loop"}'
    adapter_exit
  fi

  # 🛠️ Tool call simulation (keyword trigger)
  if [[ "$LOWER_INPUT" == *"tool"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Calling mock tool"
    adapter_exit
  fi

  # 📂 File intent simulation
  if [[ "$LOWER_INPUT" == *"read"* && "$LOWER_INPUT" == *"readme"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Reading README"
    adapter_exit
  fi

  if [[ "$LOWER_INPUT" == *"list"* ]]; then
    build_tool_call "list_files" '{"path":""}' "Listing files"
    adapter_exit
  fi

  # ✍️ Write simulation
  if [[ "$LOWER_INPUT" == *"write"* ]]; then
    build_tool_call "write_file" '{"path":"tmp/mock.txt","content":"mock data"}' "Writing file"
    adapter_exit
  fi

  # ✅ Default behavior (include tool context for parity)
  build_response "done" "[MOCK RUN] Executing: $INPUT${TOOL_CONTEXT}"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 📘 EXPLAIN
# ---------------------------------------------------------------
explain)
  build_response "done" "[MOCK EXPLAIN] $INPUT${TOOL_CONTEXT}"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 🛠️ FIX
# ---------------------------------------------------------------
fix)
  build_response "done" "[MOCK FIX] $INPUT${TOOL_CONTEXT}"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# ♻️ REFACTOR
# ---------------------------------------------------------------
refactor)
  build_response "done" "[MOCK REFACTOR] $INPUT${TOOL_CONTEXT}"
  adapter_exit
  ;;

# ---------------------------------------------------------------
# 🔎 QUERY
# ---------------------------------------------------------------
query)
  build_response "done" "[MOCK QUERY] $INPUT${TOOL_CONTEXT}"
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