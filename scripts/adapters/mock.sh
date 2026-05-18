#!/usr/bin/env bash
###################################################################
# mock.sh — Contract-based Mock Adapter (v8.1 deterministic tools)
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

append_trace_event() {
  local trace_json="$1"
  local tool_name="$2"
  local step="$3"
  local input_json="$4"
  local result_json="$5"

  jq -cn \
    --argjson trace "$trace_json" \
    --arg run_id "${AI_RUN_ID:-adapter_run}" \
    --arg tool "$tool_name" \
    --argjson step "$step" \
    --argjson input "$input_json" \
    --argjson result "$result_json" \
    '$trace + [
      {schema_version: 1, timestamp: now, run_id: $run_id, event: "tool_call", data: $tool, step: $step, meta: {input: $input}},
      {schema_version: 1, timestamp: now, run_id: $run_id, event: "tool_result", data: $tool, step: $step, meta: {result: $result}}
    ]'
}

build_simulated_trace() {
  local prompt_lower="$1"

  local file_name="hello.txt"
  local file_content="hi"
  local trace='[]'
  local step=1
  local wrote_file=0

  if [[ "$prompt_lower" =~ ([a-zA-Z0-9._-]+\.txt) ]]; then
    file_name="${BASH_REMATCH[1]}"
  fi

  if [[ "$prompt_lower" == *"content '"*"'"* ]]; then
    file_content="$(echo "$prompt_lower" | sed -n "s/.*content '\([^']*\)'.*/\1/p" | head -n1)"
    [ -z "$file_content" ] && file_content="hi"
  fi

  if [[ "$prompt_lower" == *"create"* || "$prompt_lower" == *"write"* ]]; then
    trace="$(append_trace_event "$trace" "write_file" "$step" "{\"path\":\"$file_name\",\"content\":\"$file_content\",\"overwrite\":true}" "{\"status\":\"success\",\"path\":\"$file_name\"}")"
    step=$((step + 1))
    wrote_file=1
  fi

  if [[ "$prompt_lower" == *"read"* && "$prompt_lower" == *"$file_name"* ]]; then
    local read_result
    if [ "$wrote_file" -eq 1 ]; then
      read_result="{\"status\":\"success\",\"path\":\"$file_name\",\"content\":\"$file_content\"}"
    else
      read_result="{\"status\":\"error\",\"error\":\"file_not_found\",\"path\":\"$file_name\"}"
    fi
    trace="$(append_trace_event "$trace" "read_file" "$step" "{\"path\":\"$file_name\"}" "$read_result")"
    step=$((step + 1))
  fi

  if [[ "$prompt_lower" == *"list"* && "$prompt_lower" == *"file"* ]]; then
    local files='["README.md"]'
    if [ "$wrote_file" -eq 1 ]; then
      files="[\"README.md\",\"$file_name\"]"
    fi
    trace="$(append_trace_event "$trace" "list_files" "$step" '{"path":""}' "{\"status\":\"success\",\"files\":$files}")"
  fi

  echo "$trace"
}

adapter_exit() {
  exit 0
}

command -v jq >/dev/null 2>&1 || {
  echo '{"status":"error","error":"jq_required"}'
  exit 1
}

COMMAND="${1:-}"
INPUT="${2:-}"
INPUT="${INPUT:-}"

if echo "$INPUT" | jq -e . >/dev/null 2>&1; then
  IS_JSON_INPUT=true
else
  IS_JSON_INPUT=false
  LOWER_INPUT=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]' 2>/dev/null || echo "")
fi

IS_FALLBACK="${FALLBACK_ACTIVE:-false}"

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

MAX_PROMPT_CHARS=4000
PROMPT=$(echo "$PROMPT" | head -c "$MAX_PROMPT_CHARS")

case "$COMMAND" in
run)
  if [ "$IS_FALLBACK" != "true" ] && [ "$IS_JSON_INPUT" != "true" ]; then
    SIM_TRACE="$(build_simulated_trace "$LOWER_INPUT")"
    if [ "$(echo "$SIM_TRACE" | jq 'length')" -gt 0 ]; then
      OUTPUT="Mock tool simulation complete"
      if echo "$SIM_TRACE" | jq -e 'map(select(.event == "list_files" and .meta.result.files != null and (.meta.result.files | index("hello.txt") != null))) | length > 0' >/dev/null 2>&1; then
        OUTPUT="Mock listing files: README.md, hello.txt"
      fi

      META=$(jq -cn \
        --arg mode "mock" \
        --arg provider "mock" \
        --arg output "$OUTPUT" \
        --argjson trace "$SIM_TRACE" \
        '{mode: $mode, provider: $provider, agent_output: $output, trace: $trace}')
      build_response "done" "$OUTPUT" "" "$META"
      adapter_exit
    fi

    if [[ "$LOWER_INPUT" =~ (^|[[:space:]])read([[:space:]]|$) ]] && [[ "$LOWER_INPUT" =~ (^|[[:space:]])readme([[:space:]]|$) ]]; then
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

  OUTPUT="[MOCK] ${PROMPT}"
  META=$(jq -n \
    --arg mode "$([ "$IS_FALLBACK" = "true" ] && echo "fallback" || echo "mock")" \
    --arg output "$OUTPUT" \
    '{mode: $mode, provider: "mock", agent_output: $output}')
  build_response "done" "$OUTPUT" "" "$META"
  adapter_exit
  ;;

explain|fix|refactor|query)
  OUTPUT="[MOCK ${COMMAND^^}] ${PROMPT}"
  META=$(jq -n --arg output "$OUTPUT" '{provider: "mock", agent_output: $output}')
  build_response "done" "$OUTPUT" "" "$META"
  adapter_exit
  ;;

*)
  build_response "error" "Unknown command: $COMMAND" "invalid_request"
  adapter_exit
  ;;
esac
