#!/usr/bin/env bash
###################################################################
# ndjson_integrity_tests.sh — NDJSON Trace Integrity Validation
#
# Validates:
# - trace file is valid NDJSON
# - every line parses as JSON
# - required fields exist
# - timestamps are numeric
# - event ordering is preserved
# - malformed lines are rejected
# - empty lines are not emitted
#
# Usage:
#   ./scripts/tests/ndjson_integrity_tests.sh
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

# ================================================================
# Helpers
# ================================================================

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

# ================================================================
# Execute traced run
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"

AI_TRACE=1 \
"$RUNTIME" run "ndjson integrity test" \
  > /dev/null \
  2> "$STDERR_FILE" || true

TRACE_FILE=$(
  grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    "$STDERR_FILE" \
    | tail -1
)

echo ""
echo "🧪 NDJSON Integrity Validation"
echo "=============================="
echo ""

# ================================================================
# 1️⃣ Trace file exists
# ================================================================

if test -n "${TRACE_FILE:-}" &&
   test -f "$TRACE_FILE"; then

  pass "Trace file exists"

else

  fail "Trace file exists"

fi

# ================================================================
# 2️⃣ Trace file non-empty
# ================================================================

if test -s "$TRACE_FILE"; then

  pass "Trace file non-empty"

else

  fail "Trace file non-empty"

fi

# ================================================================
# 3️⃣ Every line valid JSON
# ================================================================

INVALID_LINES=0

while IFS= read -r line; do

  if ! echo "$line" | jq empty >/dev/null 2>&1; then
    INVALID_LINES=$((INVALID_LINES + 1))
  fi

done < "$TRACE_FILE"

if [ "$INVALID_LINES" -eq 0 ]; then

  pass "Every line valid JSON"

else

  fail "Every line valid JSON"

fi

# ================================================================
# 4️⃣ No empty lines
# ================================================================

EMPTY_LINES=$(
  grep -c '^$' "$TRACE_FILE" || true
)

if [ "$EMPTY_LINES" -eq 0 ]; then

  pass "No empty lines"

else

  fail "No empty lines"

fi

# ================================================================
# 5️⃣ Required fields exist
# ================================================================

MISSING_FIELDS=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    has("schema_version") and
    has("timestamp") and
    (.timestamp | type == "number") and
    has("run_id") and
    (.run_id | type == "string") and
    has("event") and
    (.event | type == "string")
  ' >/dev/null 2>&1; then

    MISSING_FIELDS=$((MISSING_FIELDS + 1))

  fi

done < "$TRACE_FILE"

if [ "$MISSING_FIELDS" -eq 0 ]; then

  pass "Required fields present"

else

  fail "Required fields present"

fi

# ================================================================
# 6️⃣ Timestamp validation
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
# 7️⃣ Event ordering invariant
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

  pass "session_start first"

else

  fail "session_start first"

fi

if [ "$LAST_EVENT" = "session_end" ]; then

  pass "session_end last"

else

  fail "session_end last"

fi

# ================================================================
# 8️⃣ Run ID consistency
# ================================================================

RUN_IDS=$(
  cat "$TRACE_FILE" \
    | jq -r '.run_id' \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$RUN_IDS" -eq 1 ]; then

  pass "Single run_id consistency"

else

  fail "Single run_id consistency"

fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "=============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ NDJSON integrity validation FAILED"
  exit 1

fi

echo "🎉 NDJSON integrity validation passed"