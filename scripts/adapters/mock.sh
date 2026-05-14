#!/usr/bin/env bash
###################################################################
# mock.sh — Contract-based Mock Adapter (v8.0 PRODUCTION)
#
# Improvements:
# - Enforces jq dependency
# - Safe JSON vs string input handling
# - Emits agent_output for trace compatibility
# - Hardened tool trigger matching
# - Fallback-safe tool suppression
# - Robust tool discovery handling
# - Deterministic + CI-safe behavior
###################################################################

set -euo pipefail

ADAPTER_NAME="mock"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_response() {
  local status="$1"
  local output="$2"
  local error_type="${3:-}"
  local extra_meta="${4:-null}"

  if ! echo "$extra_meta" | jq empty >/dev/null 2>&1; then
    extra_meta="null"
  fi

  jq -n \
    --argjson schema_version 1 \
    --arg status "$status" \
    --arg output "$output" \
    --arg adapter "$ADAPTER_NAME" \
    --arg run_id "${AI_RUN_ID:-adapter_run}" \
    --arg run_path "${AI_RUN_PATH:-}" \
    --arg error_type "$error_type" \
    --argjson extra "$extra_meta" \
    '{
      schema_version: $schema_version,
      status: $status,
      output: $output,
      meta: (
        {
          adapter: $adapter,
          run_id: $run_id,
          run_path: $run_path,
          error: ($status == "error"),
          error_type: (if $error_type == "" then null else $error_type end)
        }
        + (if $extra == null then {} else $extra end)
      )
    }'
}

build_tool_trace_meta() {
  local tool_name="$1"
  local tool_input="$2"
  jq -n \
    --arg run_id "${AI_RUN_ID:-adapter_run}" \
    --arg tool "$tool_name" \
    --argjson input "$tool_input" \
    '{
      trace: [
        {schema_version: 1, timestamp: now, run_id: $run_id, event: "tool_call", data: $tool, step: 1, meta: {input: $input}},
        {schema_version: 1, timestamp: now, run_id: $run_id, event: "tool_result", data: $tool, step: 1, meta: {result: {status: "mocked"}}}
      ]
    }'
}

adapter_exit() {
  exit 0
}

# ================================================================
# 🔐 REQUIREMENTS
# ================================================================
command -v jq >/dev/null 2>&1 || {
  echo '{"status":"error","error":"jq_required"}'
  exit 1
}

# ================================================================
# 📥 INPUT
# ================================================================
COMMAND="${1:-}"
INPUT="${2:-}"
INPUT="${INPUT:-}"

# Detect JSON input safely
if echo "$INPUT" | jq -e . >/dev/null 2>&1; then
  IS_JSON_INPUT=true
else
  IS_JSON_INPUT=false
  LOWER_INPUT=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]' 2>/dev/null || echo "")
fi

# Detect fallback mode
IS_FALLBACK="${FALLBACK_ACTIVE:-false}"

# ================================================================
# 🧠 TOOL RESULT HANDLING
# ================================================================
if [ "$IS_JSON_INPUT" = "true" ] && echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

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

  # ------------------------------------------------------------
  # 🔧 TOOL DISCOVERY
  # ------------------------------------------------------------
  TOOL_BLOCK=""

  if command -v python3 >/dev/null 2>&1 && [ -f "${SCRIPT_DIR}/../tool_executor.py" ]; then

    if RAW_TOOLS=$(python3 "${SCRIPT_DIR}/../tool_executor.py" --list-tools 2>/dev/null); then
      :
    else
      RAW_TOOLS='{"tools":{}}'
    fi

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

# Optional prompt size guard (prevent runaway logs)
MAX_PROMPT_CHARS=4000
PROMPT=$(echo "$PROMPT" | head -c $MAX_PROMPT_CHARS)

# ================================================================
# 🧠 MOCK EXECUTION
# ================================================================
case "$COMMAND" in

run)
  # ------------------------------------------------------------
  # 🔧 TOOL TRIGGERS (disabled in fallback)
  # ------------------------------------------------------------
  if [ "$IS_FALLBACK" != "true" ] && [ "$IS_JSON_INPUT" != "true" ]; then

    if [[ "$LOWER_INPUT" =~ (^|[[:space:]])read([[:space:]]|$) ]] && \
       [[ "$LOWER_INPUT" =~ (^|[[:space:]])readme([[:space:]]|$) ]]; then
      META=$(build_tool_trace_meta "read_file" '{"path":"README.md"}')
      build_response "done" "Mock reading README" "" "$META"
      adapter_exit
    fi

    if [[ "$LOWER_INPUT" =~ (^|[[:space:]])list([[:space:]]|$) ]]; then
      META=$(build_tool_trace_meta "list_files" '{"path":""}')
      build_response "done" "Mock listing files" "" "$META"
      adapter_exit
    fi

    if [[ "$LOWER_INPUT" =~ (^|[[:space:]])loop([[:space:]]|$) ]]; then
      build_response "error" "[MOCK] Looping is not a final runtime status" "invalid_request" '{"mode":"loop"}'
      adapter_exit
    fi
  fi

  if [ "$IS_FALLBACK" != "true" ] && [ "$IS_JSON_INPUT" != "true" ] && \
     [[ "$LOWER_INPUT" =~ create ]] && [[ "$LOWER_INPUT" =~ file ]]; then
    META=$(build_tool_trace_meta "write_file" '{"path":"mock.txt","content":"hi"}')
    build_response "done" "Mock wrote file" "" "$META"
    adapter_exit
  fi

  # ------------------------------------------------------------
  # ✅ DEFAULT RESPONSE (WITH agent_output)
  # ------------------------------------------------------------
  OUTPUT="[MOCK] ${PROMPT}"

  META=$(jq -n \
    --arg mode "$([ "$IS_FALLBACK" = "true" ] && echo "fallback" || echo "mock")" \
    --arg output "$OUTPUT" \
    '{
      mode: $mode,
      provider: "mock",
      agent_output: $output
    }')

  build_response "done" "$OUTPUT" "" "$META"
  adapter_exit
  ;;

explain|fix|refactor|query)

  OUTPUT="[MOCK ${COMMAND^^}] ${PROMPT}"

  META=$(jq -n \
    --arg output "$OUTPUT" \
    '{
      provider: "mock",
      agent_output: $output
    }')

  build_response "done" "$OUTPUT" "" "$META"
  adapter_exit
  ;;

*)
  build_response "error" "Unknown command: $COMMAND" "invalid_request"
  adapter_exit
  ;;
esac