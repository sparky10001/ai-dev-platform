#!/usr/bin/env bash
###################################################################
# trace_schema_consistency_test.sh
#
# Trace Schema Consistency Validation
#
# Validates:
# - every NDJSON line is valid JSON
# - required top-level fields exist
# - field types remain consistent
# - event names are valid strings
# - timestamps are numeric
# - run_id consistency
# - data payload always object/null
# - no malformed schema drift
#
# Usage:
#   ./scripts/tests/trace_schema_consistency_test.sh
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
echo "🧪 Trace Schema Consistency Validation"
echo "======================================"
echo ""

# ================================================================
# Generate traced run
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"

AI_TRACE=1 \
"$RUNTIME" run "schema consistency validation" \
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
# 2️⃣ Every line valid JSON
# ================================================================

INVALID_JSON=0

while IFS= read -r line; do

  if ! echo "$line" | jq empty >/dev/null 2>&1; then
    INVALID_JSON=$((INVALID_JSON + 1))
  fi

done < "$TRACE_FILE"

if [ "$INVALID_JSON" -eq 0 ]; then

  pass "Every line valid JSON"

else

  fail "Every line valid JSON"
fi

# ================================================================
# 3️⃣ Required fields present
# ================================================================

SCHEMA_FAILURES=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    has("timestamp") and
    (.timestamp | type == "number") and
    has("run_id") and
    (.run_id | type == "string") and
    has("event") and
    (.event | type == "string")
  ' >/dev/null 2>&1; then

    SCHEMA_FAILURES=$((SCHEMA_FAILURES + 1))
  fi

done < "$TRACE_FILE"

if [ "$SCHEMA_FAILURES" -eq 0 ]; then

  pass "Required fields present"

else

  fail "Required fields present"
fi

# ================================================================
# 4️⃣ timestamp always numeric
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

  pass "Timestamps numeric"

else

  fail "Timestamps numeric"
fi

# ================================================================
# 5️⃣ run_id always string
# ================================================================

BAD_RUN_IDS=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    (.run_id | type) == "string"
  ' >/dev/null 2>&1; then

    BAD_RUN_IDS=$((BAD_RUN_IDS + 1))
  fi

done < "$TRACE_FILE"

if [ "$BAD_RUN_IDS" -eq 0 ]; then

  pass "run_id type stable"

else

  fail "run_id type stable"
fi

# ================================================================
# 6️⃣ event always string
# ================================================================

BAD_EVENTS=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    (.event | type) == "string"
  ' >/dev/null 2>&1; then

    BAD_EVENTS=$((BAD_EVENTS + 1))
  fi

done < "$TRACE_FILE"

if [ "$BAD_EVENTS" -eq 0 ]; then

  pass "event type stable"

else

  fail "event type stable"
fi

# ================================================================
# 7️⃣ data always object or null
# ================================================================

BAD_DATA=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    (.data == null) or
    ((.data | type) == "object")
  ' >/dev/null 2>&1; then

    BAD_DATA=$((BAD_DATA + 1))
  fi

done < "$TRACE_FILE"

if [ "$BAD_DATA" -eq 0 ]; then

  pass "data payload schema stable"

else

  fail "data payload schema stable"
fi

# ================================================================
# 8️⃣ Single run_id consistency
# ================================================================

RUN_ID_COUNT=$(
  cat "$TRACE_FILE" \
    | jq -r '.run_id' \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$RUN_ID_COUNT" -eq 1 ]; then

  pass "Single run_id consistency"

else

  fail "Single run_id consistency"
fi

# ================================================================
# 9️⃣ No empty event names
# ================================================================

EMPTY_EVENTS=$(
  cat "$TRACE_FILE" \
    | jq -r '.event' \
    | grep -c '^$' || true
)

if [ "$EMPTY_EVENTS" -eq 0 ]; then

  pass "No empty event names"

else

  fail "No empty event names"
fi

# ================================================================
# 🔟 Lifecycle schema consistency
# ================================================================

grep -q '"event": "session_start"' "$TRACE_FILE" \
  && pass "session_start schema valid" \
  || fail "session_start schema valid"

grep -q '"event": "agent_output"' "$TRACE_FILE" \
  && pass "agent_output schema valid" \
  || fail "agent_output schema valid"

grep -q '"event": "session_end"' "$TRACE_FILE" \
  && pass "session_end schema valid" \
  || fail "session_end schema valid"

# ================================================================
# Summary
# ================================================================

echo ""
echo "======================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Trace schema consistency validation FAILED"
  exit 1
fi

echo "🎉 Trace schema consistency validation passed"