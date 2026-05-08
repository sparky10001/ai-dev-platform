#!/usr/bin/env bash
###################################################################
# runtime.sh — Runtime (v8.5 FIXED)
#
# Fixes:
# - safe jq handling
# - safe trace logging
# - no jq argjson crashes
# - compatible with TraceLogger NDJSON
# - compatible with runtime_tests.sh
# - stable adapter contract validation
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ADAPTERS_DIR="${SCRIPT_DIR}/adapters"

SESSION_ID="$(date +%s)_$$"

TRACE_ENABLED="${AI_TRACE:-0}"

TRACE_DIR="${ROOT_DIR}/logs/traces"
mkdir -p "$TRACE_DIR"

TRACE_LOG="${TRACE_DIR}/ai_trace.${SESSION_ID}.log"

STEP=0

COMMAND="${1:-}"
shift || true

if [ -z "$COMMAND" ]; then
  echo "Usage: runtime.sh <command> <input>"
  exit 1
fi

MODEL_OVERRIDE=""
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --trace)
      TRACE_ENABLED=1
      ;;
    --model=*)
      MODEL_OVERRIDE="${1#*=}"
      ;;
    *)
      ARGS+=("$1")
      ;;
  esac
  shift
done

INPUT="${ARGS[*]:-}"

# ================================================================
# 🧠 MODEL ROUTING
# ================================================================

map_command_to_model() {
  case "$1" in
    query) echo "fast" ;;
    explain) echo "balanced" ;;
    fix|refactor|run) echo "heavy" ;;
    *) echo "balanced" ;;
  esac
}

MODEL="${MODEL_OVERRIDE:-$(map_command_to_model "$COMMAND")}"

# ================================================================
# 🔌 ADAPTER
# ================================================================

ADAPTER_NAME="${AI_ADAPTER:-agent}"
ADAPTER="${ADAPTERS_DIR}/${ADAPTER_NAME}.sh"

if [ ! -f "$ADAPTER" ]; then
  echo "❌ Adapter not found: $ADAPTER_NAME"
  exit 1
fi

# ================================================================
# 📝 TRACE LOGGING
# ================================================================

log_event() {

  [ "$TRACE_ENABLED" -ne 1 ] && return

  local event="$1"
  local data="${2:-{}}"

  STEP=$((STEP + 1))

  # ensure valid json
  if ! echo "$data" | jq empty >/dev/null 2>&1; then
    data="{}"
  fi

  jq -c -n \
    --arg event "$event" \
    --arg session "$SESSION_ID" \
    --argjson step "$STEP" \
    --argjson data "$data" \
    '{
      timestamp: now,
      session_id: $session,
      event: $event,
      step: $step,
      data: $data
    }' >> "$TRACE_LOG"
}

# ================================================================
# 🔄 EMIT AGENT TRACE EVENTS
# ================================================================

emit_agent_trace() {

  local trace_json="$1"

  echo "$trace_json" | jq -c '.[]?' | while read -r evt; do

    EVENT_TYPE=$(echo "$evt" | jq -r '.event // empty')

    case "$EVENT_TYPE" in

      tool_call)
        PAYLOAD=$(jq -c '{
          tool: .data,
          input: (.meta.input // {})
        }' <<< "$evt")

        log_event "tool_call" "$PAYLOAD"
        ;;

      tool_result)
        PAYLOAD=$(jq -c '{
          tool: .data,
          result: (.meta.result // {})
        }' <<< "$evt")

        log_event "tool_result" "$PAYLOAD"
        ;;

      *)
        log_event "agent_event" "$evt"
        ;;
    esac
  done
}

# ================================================================
# 🚀 RUN ADAPTER
# ================================================================

RAW_OUTPUT=$(
  timeout "${AI_TIMEOUT:-120}" \
  "$ADAPTER" \
  "$COMMAND" \
  "$INPUT" \
  "--model=$MODEL"
)

# ================================================================
# ✅ VALIDATE JSON
# ================================================================

if ! echo "$RAW_OUTPUT" | jq empty >/dev/null 2>&1; then
  echo '{
    "status":"error",
    "output":"Invalid runtime JSON",
    "meta":{"adapter":"runtime.sh"}
  }'
  exit 1
fi

RESULT=$(echo "$RAW_OUTPUT" | jq -c '.')

STATUS=$(echo "$RESULT" | jq -r '.status // empty')

if [ "$STATUS" != "done" ] && [ "$STATUS" != "error" ]; then
  echo '{
    "status":"error",
    "output":"Invalid adapter contract",
    "meta":{"adapter":"runtime.sh"}
  }'
  exit 1
fi

# ================================================================
# 📡 TRACE HANDLING
# ================================================================

TRACE=$(echo "$RESULT" | jq -c '.meta.trace // []')

if [ "$TRACE_ENABLED" -eq 1 ]; then

  emit_agent_trace "$TRACE"

  log_event "agent_output" "$(echo "$RESULT" | jq -c '{
    status,
    output
  }')"

  echo "📋 Trace: ${TRACE_LOG}" >&2
fi

# ================================================================
# 📦 SAFE FINAL ENVELOPE
# ================================================================

FINAL_OUTPUT=$(jq -n \
  --argjson result "$RESULT" \
  '{
      status: $result.status,
      output: $result.output,
      meta: $result.meta
   }'
)

echo "$FINAL_OUTPUT"