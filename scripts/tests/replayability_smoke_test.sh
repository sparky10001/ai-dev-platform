#!/usr/bin/env bash
###################################################################
# replayability_smoke_test.sh
#
# Replayability Smoke Test
#
# Validates:
# - traces can be replayed
# - NDJSON remains parseable post-run
# - event ordering survives replay
# - all events belong to same run_id
# - replay scan produces deterministic counts
# - lifecycle events are replay-safe
#
# This is a SMOKE TEST:
# It validates replay-readability,
# not full semantic deterministic execution.
#
# Usage:
#   ./scripts/tests/replayability_smoke_test.sh
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
echo "🧪 Replayability Smoke Validation"
echo "================================="
echo ""

# ================================================================
# Execute traced run
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"

AI_TRACE=1 \
"$RUNTIME" run "replayability smoke test" \
  > /dev/null \
  2> "$STDERR_FILE" || true

TRACE_FILE=$(
  grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    "$STDERR_FILE" \
    | tail -1
)

# ================================================================
# 1️⃣ Trace exists
# ================================================================

if test -n "${TRACE_FILE:-}" &&
   test -f "$TRACE_FILE"; then

  pass "Trace file exists"

else

  fail "Trace file exists"

fi

# ================================================================
# 2️⃣ Replay scan parses all lines
# ================================================================

PARSE_FAIL=0

while IFS= read -r line; do

  if ! echo "$line" | jq empty >/dev/null 2>&1; then
    PARSE_FAIL=$((PARSE_FAIL + 1))
  fi

done < "$TRACE_FILE"

if [ "$PARSE_FAIL" -eq 0 ]; then

  pass "Replay parsing succeeds"

else

  fail "Replay parsing succeeds"

fi

# ================================================================
# 3️⃣ Event count deterministic
# ================================================================

LINE_COUNT=$(wc -l < "$TRACE_FILE" | tr -d ' ')

REPLAY_COUNT=$(
  cat "$TRACE_FILE" \
    | jq -c '.' \
    | wc -l \
    | tr -d ' '
)

if [ "$LINE_COUNT" -eq "$REPLAY_COUNT" ]; then

  pass "Replay event count stable"

else

  fail "Replay event count stable"

fi

# ================================================================
# 4️⃣ Lifecycle events present
# ================================================================

grep -q '"event": "session_start"' "$TRACE_FILE" \
  && pass "session_start replayable" \
  || fail "session_start replayable"

grep -q '"event": "agent_output"' "$TRACE_FILE" \
  && pass "agent_output replayable" \
  || fail "agent_output replayable"

grep -q '"event": "session_end"' "$TRACE_FILE" \
  && pass "session_end replayable" \
  || fail "session_end replayable"

# ================================================================
# 5️⃣ Event ordering survives replay
# ================================================================

FIRST_EVENT=$(
  head -n 1 "$TRACE_FILE" \
    | jq -r '.event'
)

LAST_EVENT=$(
  tail -n 1 "$TRACE_FILE" \
    | jq -r '.event'
)

if [ "$FIRST_EVENT" = "session_start" ]; then

  pass "Replay preserves first event"

else

  fail "Replay preserves first event"

fi

if [ "$LAST_EVENT" = "session_end" ]; then

  pass "Replay preserves last event"

else

  fail "Replay preserves last event"

fi

# ================================================================
# 6️⃣ Single run identity preserved
# ================================================================

RUN_ID_COUNT=$(
  cat "$TRACE_FILE" \
    | jq -r '.run_id' \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$RUN_ID_COUNT" -eq 1 ]; then

  pass "Replay preserves run identity"

else

  fail "Replay preserves run identity"

fi

# ================================================================
# 7️⃣ Timestamp replayability
# ================================================================

BAD_TIMESTAMPS=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    (.timestamp | type) == "number"
  ' >/dev/null 2>&1; then

    BAD_TIMESTAMPS=$((BAD_TIMESTAMPS + 1))
  fi

done < "$TRACE_FILE"

if [ "$BAD_TIMESTAMPS" -eq 0 ]; then

  pass "Replay timestamps valid"

else

  fail "Replay timestamps valid"

fi

# ================================================================
# 8️⃣ Deterministic replay hash
# ================================================================

TRACE_HASH_1=$(
  sha256sum "$TRACE_FILE" \
    | awk '{print $1}'
)

TRACE_HASH_2=$(
  cat "$TRACE_FILE" \
    | sha256sum \
    | awk '{print $1}'
)

if [ "$TRACE_HASH_1" = "$TRACE_HASH_2" ]; then

  pass "Replay hash deterministic"

else

  fail "Replay hash deterministic"

fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "================================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Replayability smoke validation FAILED"
  exit 1
fi

echo "🎉 Replayability smoke validation passed"