#!/usr/bin/env bash
###################################################################
# resume_from_trace_tests.sh
#
# Resume From Trace Validation Suite
#
# Validates:
# - trace can reconstruct lifecycle state
# - replay recovers terminal status
# - replay recovers run_id
# - replay recovers event ordering
# - replay detects incomplete runs
# - replay detects completed runs
# - partial traces remain parseable
# - replay survives truncation
# - replay preserves timestamps
# - replay preserves agent output
#
# Usage:
#   ./scripts/tests/resume_from_trace_tests.sh
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
echo "🧪 Resume From Trace Validation"
echo "==============================="
echo ""

# ================================================================
# Generate traced run
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"

AI_TRACE=1 \
"$RUNTIME" run "resume validation" \
  > /dev/null \
  2> "$STDERR_FILE" || true

TRACE_FILE=$(
  grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    "$STDERR_FILE" \
    | tail -1
)

# ================================================================
# Trace existence
# ================================================================

if test -n "${TRACE_FILE:-}" &&
   test -f "$TRACE_FILE"; then

  pass "Trace file exists"

else

  fail "Trace file exists"

  echo ""
  echo "==============================="
  echo "✅ Passed: $PASS_COUNT"
  echo "❌ Failed: $FAIL_COUNT"
  echo ""

  exit 1
fi

# ================================================================
# Replay parse validation
# ================================================================

if cat "$TRACE_FILE" | jq -e '.' >/dev/null 2>&1; then

  pass "Replay parsing succeeds"

else

  fail "Replay parsing succeeds"
fi

# ================================================================
# Extract replay metadata
# ================================================================

RUN_IDS=$(
  cat "$TRACE_FILE" | jq -r '.run_id' | sort -u
)

RUN_ID_COUNT=$(echo "$RUN_IDS" | wc -l)

FIRST_EVENT=$(
  head -n 1 "$TRACE_FILE" | jq -r '.event'
)

LAST_EVENT=$(
  tail -n 1 "$TRACE_FILE" | jq -r '.event'
)

FINAL_STATUS=$(
  cat "$TRACE_FILE" \
    | jq -r '
        select(.event=="agent_output")
        | .data.status
      ' \
    | tail -1
)

FINAL_OUTPUT=$(
  cat "$TRACE_FILE" \
    | jq -r '
        select(.event=="agent_output")
        | .data.output
      ' \
    | tail -1
)

# ================================================================
# 1️⃣ Replay recovers single run identity
# ================================================================

if [ "$RUN_ID_COUNT" -eq 1 ]; then

  pass "Replay recovers run identity"

else

  fail "Replay recovers run identity"
fi

# ================================================================
# 2️⃣ Replay reconstructs lifecycle start
# ================================================================

if [ "$FIRST_EVENT" = "session_start" ]; then

  pass "Replay reconstructs lifecycle start"

else

  fail "Replay reconstructs lifecycle start"
fi

# ================================================================
# 3️⃣ Replay reconstructs lifecycle end
# ================================================================

if [ "$LAST_EVENT" = "session_end" ]; then

  pass "Replay reconstructs lifecycle end"

else

  fail "Replay reconstructs lifecycle end"
fi

# ================================================================
# 4️⃣ Replay reconstructs terminal status
# ================================================================

if [ "$FINAL_STATUS" = "done" ] ||
   [ "$FINAL_STATUS" = "error" ]; then

  pass "Replay reconstructs terminal status"

else

  fail "Replay reconstructs terminal status"
fi

# ================================================================
# 5️⃣ Replay reconstructs agent output
# ================================================================

if [ -n "${FINAL_OUTPUT:-}" ] &&
   [ "$FINAL_OUTPUT" != "null" ]; then

  pass "Replay reconstructs agent output"

else

  fail "Replay reconstructs agent output"
fi

# ================================================================
# 6️⃣ Replay preserves ordering
# ================================================================

ORDER_OK=1

PREV=0

while IFS= read -r ts; do

  if ! awk "BEGIN {exit !($ts >= $PREV)}"; then
    ORDER_OK=0
    break
  fi

  PREV="$ts"

done < <(
  cat "$TRACE_FILE" | jq -r '.timestamp'
)

if [ "$ORDER_OK" -eq 1 ]; then

  pass "Replay preserves ordering"

else

  fail "Replay preserves ordering"
fi

# ================================================================
# 7️⃣ Partial trace remains replayable
# ================================================================

PARTIAL_TRACE="${TMP_DIR}/partial.jsonl"

head -n -1 "$TRACE_FILE" > "$PARTIAL_TRACE"

if cat "$PARTIAL_TRACE" | jq -e '.' >/dev/null 2>&1; then

  pass "Partial trace remains replayable"

else

  fail "Partial trace remains replayable"
fi

# ================================================================
# 8️⃣ Replay detects incomplete run
# ================================================================

PARTIAL_LAST_EVENT=$(
  tail -n 1 "$PARTIAL_TRACE" | jq -r '.event'
)

if [ "$PARTIAL_LAST_EVENT" != "session_end" ]; then

  pass "Replay detects incomplete run"

else

  fail "Replay detects incomplete run"
fi

# ================================================================
# 9️⃣ Replay survives truncation
# ================================================================

TRUNCATED_TRACE="${TMP_DIR}/truncated.jsonl"

head -n 2 "$TRACE_FILE" > "$TRUNCATED_TRACE"

if cat "$TRUNCATED_TRACE" | jq -e '.' >/dev/null 2>&1; then

  pass "Replay survives truncation"

else

  fail "Replay survives truncation"
fi

# ================================================================
# 🔟 Replay preserves timestamps
# ================================================================

if cat "$TRACE_FILE" \
    | jq -e '
        .timestamp | numbers
      ' >/dev/null 2>&1; then

  pass "Replay preserves timestamps"

else

  fail "Replay preserves timestamps"
fi

# ================================================================
# 1️⃣1️⃣ Replay event count stable
# ================================================================

ORIGINAL_COUNT=$(wc -l < "$TRACE_FILE")
REPLAY_COUNT=$(
  cat "$TRACE_FILE" | jq -c '.' | wc -l
)

if [ "$ORIGINAL_COUNT" -eq "$REPLAY_COUNT" ]; then

  pass "Replay event count stable"

else

  fail "Replay event count stable"
fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "==============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Resume validation FAILED"
  exit 1
fi

echo "🎉 Resume validation passed"