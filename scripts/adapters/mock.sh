#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock Adapter (v7.1)
#
# Fixes from v7:
# - Tool triggers in mock.sh guarded for fallback mode
#   (was triggering unexpected tool calls during fallback)
# - No symlinks
###################################################################

set -euo pipefail

ADAPTER_NAME="mock"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

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
        if (.tools | length) == 0 then ""
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
# 🧠 MOCK EXECUTION
# ================================================================

case "$COMMAND" in

run)
  # ---- Tool triggers only when NOT in fallback mode ----
  # Fix v7.1: tool triggers suppressed during fallback to prevent
  # unexpected tool calls when mock is acting as last-resort provider
  if [ "$IS_FALLBACK" != "true" ]; then

    if [[ "$LOWER_INPUT" == *"read"* && "$LOWER_INPUT" == *"readme"* ]]; then
      build_tool_call "read_file" '{"path":"README.md"}' "Mock reading README"
      adapter_exit
    fi

    if [[ "$LOWER_INPUT" == *"list"* ]]; then
      build_tool_call "list_files" '{"path":""}' "Mock listing files"
      adapter_exit
    fi

    if [[ "$LOWER_INPUT" == *"loop"* ]]; then
      build_response "continue" "[MOCK] Looping..." "" '{"mode":"loop"}'
      adapter_exit
    fi

  fi

  # Default safe output
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
