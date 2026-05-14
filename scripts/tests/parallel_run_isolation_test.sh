#!/usr/bin/env bash
###################################################################
# parallel_run_isolation_test.sh
#
# HIGH VALUE VALIDATION
#
# Validates:
# - concurrent runtime execution
# - unique run directories
# - unique trace files
# - no trace cross-contamination
# - no run_id leakage
# - event isolation across runs
# - concurrent finalize safety
#
# Usage:
#   ./scripts/tests/parallel_run_isolation_test.sh
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
echo "🧪 Parallel Run Isolation Validation"
echo "===================================="
echo ""

# ================================================================
# Launch concurrent runs
# ================================================================

RUN_COUNT=5

PIDS=()

for i in $(seq 1 "$RUN_COUNT"); do

  STDERR_FILE="${TMP_DIR}/stderr_${i}.log"

  (
    AI_TRACE=1 \
    "$RUNTIME" run "parallel-test-${i}" \
      > /dev/null \
      2> "$STDERR_FILE"
  ) &

  PIDS+=($!)

done

# ================================================================
# Wait for completion
# ================================================================

for pid in "${PIDS[@]}"; do
  wait "$pid" || true
done

# ================================================================
# Collect trace files
# ================================================================

TRACE_FILES=()

for i in $(seq 1 "$RUN_COUNT"); do

  STDERR_FILE="${TMP_DIR}/stderr_${i}.log"

  TRACE_FILE=$(
    grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
      "$STDERR_FILE" \
      | tail -1
  )

  if [ -n "${TRACE_FILE:-}" ]; then
    TRACE_FILES+=("$TRACE_FILE")
  fi

done

# ================================================================
# 1️⃣ Correct trace count
# ================================================================

if [ "${#TRACE_FILES[@]}" -eq "$RUN_COUNT" ]; then

  pass "All trace files emitted"

else

  fail "All trace files emitted"

fi

# ================================================================
# 2️⃣ All trace files exist
# ================================================================

MISSING=0

for trace in "${TRACE_FILES[@]}"; do

  if ! test -f "$trace"; then
    MISSING=$((MISSING + 1))
  fi

done

if [ "$MISSING" -eq 0 ]; then

  pass "All trace files exist"

else

  fail "All trace files exist"

fi

# ================================================================
# 3️⃣ Unique trace paths
# ================================================================

UNIQUE_TRACE_COUNT=$(
  printf "%s\n" "${TRACE_FILES[@]}" \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$UNIQUE_TRACE_COUNT" -eq "$RUN_COUNT" ]; then

  pass "Unique trace paths"

else

  fail "Unique trace paths"

fi

# ================================================================
# 4️⃣ Unique run IDs
# ================================================================

RUN_IDS=()

for trace in "${TRACE_FILES[@]}"; do

  RUN_ID=$(
    head -n 1 "$trace" \
      | jq -r '.run_id'
  )

  RUN_IDS+=("$RUN_ID")

done

UNIQUE_RUN_IDS=$(
  printf "%s\n" "${RUN_IDS[@]}" \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$UNIQUE_RUN_IDS" -eq "$RUN_COUNT" ]; then

  pass "Unique run IDs"

else

  fail "Unique run IDs"

fi

# ================================================================
# 5️⃣ No cross-trace contamination
# ================================================================

CONTAMINATION=0

for trace in "${TRACE_FILES[@]}"; do

  EXPECTED_RUN_ID=$(
    head -n 1 "$trace" \
      | jq -r '.run_id'
  )

  BAD_LINES=$(
    cat "$trace" \
      | jq -r '.run_id' \
      | grep -vc "^${EXPECTED_RUN_ID}$" || true
  )

  if [ "$BAD_LINES" -ne 0 ]; then
    CONTAMINATION=$((CONTAMINATION + 1))
  fi

done

if [ "$CONTAMINATION" -eq 0 ]; then

  pass "No cross-trace contamination"

else

  fail "No cross-trace contamination"

fi

# ================================================================
# 6️⃣ All traces valid NDJSON
# ================================================================

INVALID=0

for trace in "${TRACE_FILES[@]}"; do

  while IFS= read -r line; do

    if ! echo "$line" | jq empty >/dev/null 2>&1; then
      INVALID=$((INVALID + 1))
    fi

  done < "$trace"

done

if [ "$INVALID" -eq 0 ]; then

  pass "Concurrent NDJSON integrity"

else

  fail "Concurrent NDJSON integrity"

fi

# ================================================================
# 7️⃣ Lifecycle completeness
# ================================================================

BROKEN=0

for trace in "${TRACE_FILES[@]}"; do

  grep -q '"event": "session_start"' "$trace" || BROKEN=$((BROKEN + 1))
  grep -q '"event": "agent_output"' "$trace" || BROKEN=$((BROKEN + 1))
  grep -q '"event": "session_end"' "$trace" || BROKEN=$((BROKEN + 1))

done

if [ "$BROKEN" -eq 0 ]; then

  pass "Lifecycle completeness"

else

  fail "Lifecycle completeness"

fi

# ================================================================
# 8️⃣ finalize_run persistence
# ================================================================

PERSIST_FAIL=0

for trace in "${TRACE_FILES[@]}"; do

  if ! test -s "$trace"; then
    PERSIST_FAIL=$((PERSIST_FAIL + 1))
  fi

done

if [ "$PERSIST_FAIL" -eq 0 ]; then

  pass "Concurrent finalize persistence"

else

  fail "Concurrent finalize persistence"

fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "===================================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Parallel isolation validation FAILED"
  exit 1

fi

echo "🎉 Parallel isolation validation passed"