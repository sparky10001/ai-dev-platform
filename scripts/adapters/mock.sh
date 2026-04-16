#!/bin/bash
###################################################################
# mock.sh — Contract-based Mock AI Adapter (v6 production)
#
# Fully aligned with http-agent/openai adapters
# - Tool-aware prompting (human-readable)
# - Tool result handling (first-class)
# - Deterministic behavior
# - Contract-safe outputs
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

  PROMPT="A tool was used.

Tool: ${TOOL_NAME}
Result:
${TOOL_RESULT}

Decide the next step."

else

  # ---- Validate ----
  if [ -z "$COMMAND" ]; then
    build_response "error" "Missing command" "invalid_request"
    adapter_exit
  fi

  # ---- Context ----
  CONTEXT=""
  [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

  # ================================================================
  # 🔌 TOOL DISCOVERY (PARITY WITH REAL ADAPTERS)
  # ================================================================
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

  # ================================================================
  # 🧠 TOOL USAGE INSTRUCTIONS (PARITY)
  # ================================================================
  SYSTEM_INSTRUCTIONS="You are an AI assistant with access to tools.

When you need external data, you MUST call a tool.

To call a tool, respond ONLY with valid JSON:
{
  \"status\": \"tool_call\",
  \"tool_call\": {
    \"name\": \"tool_name\",
    \"input\": { ... }
  }
}

Rules:
- Do NOT include explanations when calling tools
- ONLY output JSON for tool calls
- If no tool is needed, respond normally"

  # ---- Prompt ----
  case "$COMMAND" in
    run)      USER_PROMPT="${INPUT}" ;;
    fix)      USER_PROMPT="Fix this:\n${INPUT}" ;;
    explain)  USER_PROMPT="Explain clearly:\n${INPUT}" ;;
    refactor) USER_PROMPT="Refactor this:\n${INPUT}" ;;
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
# 🧠 MOCK EXECUTION ENGINE
# ================================================================

case "$COMMAND" in

run)

  # 🔁 Loop simulation
  if [[ "$LOWER_INPUT" == *"loop"* ]]; then
    build_response "continue" "[MOCK] Looping..." "" '{"mode":"loop"}'
    adapter_exit
  fi

  # 🛠️ Tool triggers
  if [[ "$LOWER_INPUT" == *"tool"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Calling mock tool"
    adapter_exit
  fi

  if [[ "$LOWER_INPUT" == *"read"* && "$LOWER_INPUT" == *"readme"* ]]; then
    build_tool_call "read_file" '{"path":"README.md"}' "Reading README"
    adapter_exit
  fi

  if [[ "$LOWER_INPUT" == *"list"* ]]; then
    build_tool_call "list_files" '{"path":""}' "Listing files"
    adapter_exit
  fi

  if [[ "$LOWER_INPUT" == *"write"* ]]; then
    build_tool_call "write_file" '{"path":"tmp/mock.txt","content":"mock data"}' "Writing file"
    adapter_exit
  fi

  # ✅ Default
  build_response "done" "[MOCK RUN] ${PROMPT}"
  adapter_exit
  ;;

explain)
  build_response "done" "[MOCK EXPLAIN] ${PROMPT}"
  adapter_exit
  ;;

fix)
  build_response "done" "[MOCK FIX] ${PROMPT}"
  adapter_exit
  ;;

refactor)
  build_response "done" "[MOCK REFACTOR] ${PROMPT}"
  adapter_exit
  ;;

query)
  build_response "done" "[MOCK QUERY] ${PROMPT}"
  adapter_exit
  ;;

*)
  build_response "error" "[MOCK ERROR] Unknown command: $COMMAND" "invalid_request"
  adapter_exit
  ;;
esac