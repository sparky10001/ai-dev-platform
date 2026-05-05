#!/bin/bash
###################################################################
# runtime.sh — AI Runtime (v7.4)
#
# Fixes from v7.3:
# - CRITICAL: removed PARSED_JSON="" + PARSED_OUTPUT="" variable
#   reset that was wiping parsed adapter output before contract
#   checks and field extraction — caused all agent tool calls
#   to appear broken (empty STATUS/OUTPUT/trace)
# - Consolidated to single PARSED_OUTPUT variable throughout
# - Trace merge now correctly reads from PARSED_OUTPUT
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
ADAPTERS_DIR="${SCRIPT_DIR}/adapters"

# ---- Session + Trace ----
# seconds+PID — portable across Linux and macOS (%N not on macOS)
SESSION_ID="$(date +%s)_$$"
TRACE_ENABLED=0
TRACE_LOG="${SCRIPT_DIR}/../.ai_trace.${SESSION_ID}.log"

# ---------------------------------------------------------------
# 🔧 Load env
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Check AI_TRACE env var (set by ai CLI) OR --trace flag
[ "${AI_TRACE:-0}" = "1" ] && TRACE_ENABLED=1

# ---------------------------------------------------------------
# 🧠 Command → Model Tier Mapping
# ---------------------------------------------------------------
map_command_to_model() {
  case "$1" in
    query)    echo "fast" ;;
    explain)  echo "balanced" ;;
    fix)      echo "heavy" ;;
    refactor) echo "heavy" ;;
    run)      echo "heavy" ;;
    *)        echo "balanced" ;;
  esac
}

# ---------------------------------------------------------------
# 📥 Args
# ---------------------------------------------------------------
COMMAND="${1:-}"
shift || true

if [ -z "$COMMAND" ]; then
  echo "Usage: runtime.sh [run|explain|refactor|fix|query] <input>"
  exit 1
fi

MODEL_OVERRIDE=""
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --trace)     TRACE_ENABLED=1 ;;
    --model=*)   MODEL_OVERRIDE="${1#*=}" ;;
    *)           ARGS+=("$1") ;;
  esac
  shift
done

INPUT="${ARGS[*]:-}"

# ---------------------------------------------------------------
# 🎯 Resolve model tier
# ---------------------------------------------------------------
if [ -n "$MODEL_OVERRIDE" ]; then
  RESOLVED_MODEL="$MODEL_OVERRIDE"
elif [ -n "${ACTIVE_MODEL:-}" ]; then
  RESOLVED_MODEL="$ACTIVE_MODEL"
else
  RESOLVED_MODEL="$(map_command_to_model "$COMMAND")"
fi

# ---------------------------------------------------------------
# 🔌 Adapter selection
# ---------------------------------------------------------------
ADAPTER_NAME="${AI_ADAPTER:-agent}"
ADAPTER="${ADAPTERS_DIR}/${ADAPTER_NAME}.sh"

if [ ! -f "$ADAPTER" ]; then
  echo "❌ Adapter not found: $ADAPTER_NAME (looked in $ADAPTERS_DIR)"
  exit 1
fi

# ---------------------------------------------------------------
# 🧾 Trace helpers
# ---------------------------------------------------------------
STEP=0

log_event() {
  [ "$TRACE_ENABLED" -ne 1 ] && return

  local event="$1"
  local data="$2"

  STEP=$((STEP+1))

  jq -n \
    --arg event "$event" \
    --arg session "$SESSION_ID" \
    --argjson data "$data" \
    --argjson step "$STEP" \
    '{
      event: $event,
      session_id: $session,
      step: $step,
      data: $data,
      timestamp: now
    }' >> "$TRACE_LOG" 2>/dev/null || true
}

# Initialize trace file
if [ "$TRACE_ENABLED" -eq 1 ]; then
  : > "$TRACE_LOG"
  log_event "start" "$(jq -n \
    --arg input "$INPUT" \
    --arg command "$COMMAND" \
    --arg model "$RESOLVED_MODEL" \
    --arg adapter "$ADAPTER_NAME" \
    '{input:$input, command:$command, model:$model, adapter:$adapter}')"
fi

# ---------------------------------------------------------------
# 🚀 Execute adapter
# ---------------------------------------------------------------
RAW_OUTPUT=""
EXIT_CODE=0
RUNTIME_TIMEOUT="${AI_TIMEOUT:-120}"

RAW_OUTPUT=$(timeout "$RUNTIME_TIMEOUT" \
  "$ADAPTER" "$COMMAND" "$INPUT" "--model=$RESOLVED_MODEL") || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  if [ $EXIT_CODE -eq 124 ]; then
    echo "❌ Adapter timed out (${RUNTIME_TIMEOUT}s)"
  else
    echo "❌ Adapter execution failed (exit $EXIT_CODE)"
  fi
  log_event "runtime_error" \
    "$(jq -n --argjson code "$EXIT_CODE" '{exit_code:$code}')"
  exit 1
fi

# ---------------------------------------------------------------
# ❌ Validate JSON
# ---------------------------------------------------------------
if ! echo "$RAW_OUTPUT" | jq empty >/dev/null 2>&1; then
  echo "❌ Invalid JSON from adapter"
  echo "$RAW_OUTPUT"
  log_event "invalid_json" \
    "$(jq -n --arg raw "$RAW_OUTPUT" '{raw:$raw}')"
  exit 1
fi

# ---------------------------------------------------------------
# ✅ Parse into single variable — used everywhere below
# Fix v7.4: was split across PARSED_JSON + PARSED_OUTPUT with
# a reset block in the middle that wiped both variables
# ---------------------------------------------------------------
PARSED_OUTPUT=$(echo "$RAW_OUTPUT" | jq -c '.')

log_event "agent_output" "$PARSED_OUTPUT"

# ---------------------------------------------------------------
# 🔥 Merge agent trace into runtime trace log
# Reads from PARSED_OUTPUT — not from a reset empty variable
# ---------------------------------------------------------------
if [ "$TRACE_ENABLED" -eq 1 ]; then
  AGENT_TRACE=$(echo "$PARSED_OUTPUT" | jq -c '.meta.trace // []' \
    2>/dev/null || echo "[]")

  if [ "$AGENT_TRACE" != "[]" ]; then
    echo "$AGENT_TRACE" | jq -c \
      --arg session "$SESSION_ID" \
      '.[] | .session_id = $session' \
      >> "$TRACE_LOG" 2>/dev/null || true
  fi
fi

# ---------------------------------------------------------------
# 🔒 Enforce strict contract
# ---------------------------------------------------------------
if ! echo "$PARSED_OUTPUT" | jq -e '
  has("status") and
  (.status == "done" or .status == "error")
' >/dev/null 2>&1; then
  echo "❌ Invalid adapter contract (missing/invalid status)"
  exit 1
fi

if ! echo "$PARSED_OUTPUT" | jq -e 'has("output")' >/dev/null 2>&1; then
  echo "❌ Invalid adapter contract (missing output)"
  exit 1
fi

# ---------------------------------------------------------------
# 📦 Extract fields
# ---------------------------------------------------------------
STATUS=$(echo "$PARSED_OUTPUT" | jq -r '.status')
OUTPUT=$(echo "$PARSED_OUTPUT" | jq -r '.output // empty')
MODEL=$(echo "$PARSED_OUTPUT" | jq -r '.meta.model // empty')

# ---------------------------------------------------------------
# 🧾 End trace
# ---------------------------------------------------------------
if [ "$TRACE_ENABLED" -eq 1 ]; then
  log_event "end" "$(jq -n \
    --arg status "$STATUS" \
    --arg model "$MODEL" \
    '{status:$status, model:$model}')"

  echo "📋 Trace: $TRACE_LOG" >&2
fi

# ---------------------------------------------------------------
# 📤 Output
# ---------------------------------------------------------------
case "$STATUS" in
  done)
    [ -n "$OUTPUT" ] && echo "$OUTPUT"
    ;;
  error)
    echo "❌ $OUTPUT"
    exit 1
    ;;
  *)
    echo "⚠️ Unknown status: $STATUS"
    exit 1
    ;;
esac
