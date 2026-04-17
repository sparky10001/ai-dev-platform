#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock Adapter (v7 production)
#
# Aligned with fallback chain model:
# - Safe as final fallback provider
# - Deterministic behavior
# - No infinite loops
# - Contract-consistent metadata
###################################################################

set -euo pipefail

COMMAND="${1:-}"
INPUT="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ADAPTER_NAME="mock"

source "${SCRIPT_DIR}/_base.sh"

INPUT="${INPUT:-}"
LOWER_INPUT=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]' 2>/dev/null || echo "")

# Detect if running inside fallback chain
IS_FALLBACK="${FALLBACK_ACTIVE:-false}"

# ================================================================
# 🧠 TOOL RESULT HANDLING
# ================================================================
if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
  TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

  PROMPT="Tool '${TOOL_NAME}' returned:
${TOOL_RESULT}

Decide the next step."

else

  if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
  fi

  CONTEXT=""
  [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

  TOOL_BLOCK=""

  if command -v python3 >/dev/null 2>&1 && [ -f "${SCRIPT_DIR}/../tool_executor.py" ]; then
    RAW_TOOLS=$(python3 "${SCRIPT_DIR}/../tool_executor.py" --list-tools 2>/dev/null || echo '{"tools":{}}')

    if echo "$RAW_TOOLS" | jq -e '.tools' >/dev/null 2>&1; then
      TOOL_BLOCK=$(echo "$RAW_TOOLS" | jq -r '
        if (.tools | length) == 0 then
          ""
        else
          "Available tools:\n" +
          (
            .tools
            | to_entries
            | map("- " + .value.name + ": " + (.value.description // ""))
            | join("\n")
          )
        end
      ')
    fi
  fi

  SYSTEM_INSTRUCTIONS="You are a mock AI system.

Follow tool rules strictly.
Be deterministic."

  case "$COMMAND" in
    run)      USER_PROMPT="${INPUT}" ;;
    fix)      USER_PROMPT="Fix this:\n${INPUT}" ;;
    explain)  USER_PROMPT="Explain:\n${INPUT}" ;;
    refactor) USER_PROMPT="Refactor:\n${INPUT}" ;;
    query)    USER_PROMPT="${INPUT}" ;;
    *)
      build_response "error" "Unknown command: $COMMAND" "invalid_request"
      adapter_exit
      ;;
  esac

  PROMPT="${SYSTEM_INSTRUCTIONS}

${CONTEXT}${TOOL_BLOCK}

User request:
${USER_PROMPT}"
fi

# ================================================================
# 🧠 MOCK EXECUTION (SAFE)
# ================================================================

case "$COMMAND" in

run)

  # ---- Tool triggers (allowed even in fallback) ----
  if [[ "$LOWER_INPUT" == *"read"* && "$LOWER_INPUT" == *"readme"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Mock reading README"
    adapter_exit
  fi

  if [[ "$LOWER_INPUT" == *"list"* ]]; then
    build_tool_call "list_files" '{"path":""}' "Mock listing files"
    adapter_exit
  fi

  # ---- Loop simulation ONLY outside fallback ----
  if [[ "$LOWER_INPUT" == *"loop"* && "$IS_FALLBACK" != "true" ]]; then
    build_response "continue" "[MOCK] Looping..." "" '{"mode":"loop"}'
    adapter_exit
  fi

  # ---- Default SAFE output ----
  build_response "done" "[MOCK] ${PROMPT}" "" \
    "$(jq -n \
      --arg mode "$([ "$IS_FALLBACK" = "true" ] && echo "fallback" || echo "mock")" \
      '{mode:$mode, provider:"mock"}')"
  adapter_exit
  ;;

explain|fix|refactor|query)

  build_response "done" "[MOCK ${COMMAND^^}] ${PROMPT}" "" \
    '{"provider":"mock"}'
  adapter_exit
  ;;

*)
  build_response "error" "Unknown command: $COMMAND" "invalid_request"
  adapter_exit
  ;;
esac