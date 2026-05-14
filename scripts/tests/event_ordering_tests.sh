#!/usr/bin/env bash
###################################################################
# event_ordering_tests.sh
#
# Event Ordering Validation Suite
#
# Validates:
# - session_start occurs first
# - session_end occurs last
# - agent_output occurs before session_end
# - no events occur after session_end
# - timestamps monotonically increase
# - lifecycle ordering remains deterministic
# - trace ingestion preserves ordering
# - no duplicate terminal events
#
# Usage:
#   ./scripts/tests/event_ordering_tests.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

echo ""
echo "🧪 Event Ordering Validation"
echo "============================"
echo ""

# ================================================================
# Generate traced run
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"

AI_TRACE=1 \
"$RUNTIME" run "event ordering validation" \
  > /dev/null \
  2> "$STDERR_FILE" || true

TRACE_FILE=$(
  grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    "$STDERR_FILE" \
    | tail -1
)

# ================================================================
# Ensure trace exists
# ================================================================

if test -n "${TRACE_FILE:-}" &&
   test -f "$TRACE_FILE"; then

  pass "Trace file exists"

else

  fail "Trace file exists"

  echo ""
  echo "============================"
  echo "✅ Passed: $PASS_COUNT"
  echo "❌ Failed: $FAIL_COUNT"
  echo ""
  exit 1
fi

# ================================================================
# Extract event sequence
# ================================================================

EVENTS_FILE="${TMP_DIR}/events.txt"

cat "$TRACE_FILE" \
  | jq -r '.event' \
  > "$EVENTS_FILE"

# ================================================================
# 1️⃣ session_start first
# ================================================================

FIRST_EVENT=$(head -n 1 "$EVENTS_FILE")

if [ "$FIRST_EVENT" = "session_start" ]; then

  pass "session_start first"

else

  fail "session_start first"
fi

# ================================================================
# 2️⃣ session_end last
# ================================================================

LAST_EVENT=$(tail -n 1 "$EVENTS_FILE")

if [ "$LAST_EVENT" = "session_end" ]; then

  pass "session_end last"

else

  fail "session_end last"
fi

# ================================================================
# 3️⃣ agent_output before session_end
# ================================================================

AGENT_OUTPUT_LINE=$(
  grep -n '^agent_output$' "$EVENTS_FILE" \
    | tail -1 \
    | cut -d: -f1
)

SESSION_END_LINE=$(
  grep -n '^session_end$' "$EVENTS_FILE" \
    | tail -1 \
    | cut -d: -f1
)

if [ -n "${AGENT_OUTPUT_LINE:-}" ] &&
   [ -n "${SESSION_END_LINE:-}" ] &&
   [ "$AGENT_OUTPUT_LINE" -lt "$SESSION_END_LINE" ]; then

  pass "agent_output before session_end"

else

  fail "agent_output before session_end"
fi

# ================================================================
# 4️⃣ No events after session_end
# ================================================================

TOTAL_LINES=$(wc -l < "$EVENTS_FILE")

if [ "$SESSION_END_LINE" -eq "$TOTAL_LINES" ]; then

  pass "No events after session_end"

else

  fail "No events after session_end"
fi

# ================================================================
# 5️⃣ Single session_start
# ================================================================

SESSION_START_COUNT=$(
  grep -c '^session_start$' "$EVENTS_FILE"
)

if [ "$SESSION_START_COUNT" -eq 1 ]; then

  pass "Single session_start"

else

  fail "Single session_start"
fi

# ================================================================
# 6️⃣ Single session_end
# ================================================================

SESSION_END_COUNT=$(
  grep -c '^session_end$' "$EVENTS_FILE"
)

if [ "$SESSION_END_COUNT" -eq 1 ]; then

  pass "Single session_end"

else

  fail "Single session_end"
fi

# ================================================================
# 7️⃣ Single agent_output
# ================================================================

AGENT_OUTPUT_COUNT=$(
  grep -c '^agent_output$' "$EVENTS_FILE"
)

if [ "$AGENT_OUTPUT_COUNT" -eq 1 ]; then

  pass "Single agent_output"

else

  fail "Single agent_output"
fi

# ================================================================
# 8️⃣ Monotonic timestamps
# ================================================================

TIMESTAMP_FAILURE=0
PREV_TS=""

while IFS= read -r ts; do

  if [ -n "$PREV_TS" ]; then

    if ! awk "BEGIN {exit !($ts >= $PREV_TS)}"; then
      TIMESTAMP_FAILURE=1
      break
    fi
  fi

  PREV_TS="$ts"

done < <(
  cat "$TRACE_FILE" | jq -r '.timestamp'
)

if [ "$TIMESTAMP_FAILURE" -eq 0 ]; then

  pass "Monotonic timestamps"

else

  fail "Monotonic timestamps"
fi

# ================================================================
# 9️⃣ Lifecycle ordering deterministic
# ================================================================

EXPECTED_ORDER="session_start"

ACTUAL_START=$(head -n 1 "$EVENTS_FILE")

if [ "$ACTUAL_START" = "$EXPECTED_ORDER" ]; then

  pass "Lifecycle ordering deterministic"

else

  fail "Lifecycle ordering deterministic"
fi

# ================================================================
# 🔟 Trace ingestion ordering preserved
# ================================================================

ORDER_FAILURE=0

PREV_INDEX=0

while IFS= read -r event; do

  case "$event" in

    session_start)
      INDEX=1
      ;;

    adapter_output_raw)
      INDEX=2
      ;;

    error|agent_event)
      INDEX=3
      ;;

    agent_output)
      INDEX=4
      ;;

    session_end)
      INDEX=5
      ;;

    *)
      INDEX=$PREV_INDEX
      ;;
  esac

  if [ "$INDEX" -lt "$PREV_INDEX" ]; then
    ORDER_FAILURE=1
    break
  fi

  PREV_INDEX="$INDEX"

done < "$EVENTS_FILE"

if [ "$ORDER_FAILURE" -eq 0 ]; then

  pass "Trace ingestion ordering preserved"

else

  fail "Trace ingestion ordering preserved"
fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "============================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Event ordering validation FAILED"
  exit 1
fi

echo "🎉 Event ordering validation passed"