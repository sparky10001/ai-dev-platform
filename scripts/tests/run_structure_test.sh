#!/usr/bin/env bash
###################################################################
# run_structure_test.sh — Run Structure Validation (CRITICAL)
#
# Validates:
# - run object is created
# - trace file exists
# - session_start is emitted
# - agent_output is emitted
# - session_end is always emitted
# - finalize_run is called (trace persists)
#
# Usage:
#   ./scripts/tests/run_structure_test.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

PASS=0
FAIL=0

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass() { echo "✅ $1"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

run() {
  "$@" > "$TMP/out.log" 2> "$TMP/err.log" || true
}

echo ""
echo "🧪 Run Structure Validation"
echo "==========================="
echo ""

# ============================================================
# 1. Run execution
# ============================================================

AI_ADAPTER=agent \
"$RUNTIME" run "hello structure test" --trace \
  > "$TMP/out.log" \
  2> "$TMP/err.log" || true

TRACE_PATH=$(grep -oE '/workspace/runs/[^ ]+/trace.jsonl' "$TMP/err.log" | tail -1 || true)

if [ -z "${TRACE_PATH:-}" ]; then
  fail "Trace path emitted"
else
  pass "Trace path emitted"
fi

# ============================================================
# 2. Trace file exists
# ============================================================

if [ -n "${TRACE_PATH:-}" ] && [ -f "$TRACE_PATH" ]; then
  pass "Trace file exists"
else
  fail "Trace file exists"
fi

# ============================================================
# 3. Required events exist
# ============================================================

if [ -f "$TRACE_PATH" ]; then

  if grep -q '"event": "session_start"' "$TRACE_PATH"; then
    pass "session_start emitted"
  else
    fail "session_start emitted"
  fi

  if grep -q '"event": "agent_output"' "$TRACE_PATH"; then
    pass "agent_output emitted"
  else
    fail "agent_output emitted"
  fi

  if grep -q '"event": "session_end"' "$TRACE_PATH"; then
    pass "session_end emitted"
  else
    fail "session_end emitted"
  fi

else
  fail "trace file readable"
  fail "session_start emitted"
  fail "agent_output emitted"
  fail "session_end emitted"
fi

# ============================================================
# 4. finalize_run sanity (indirect check)
# ============================================================

if [ -f "$TRACE_PATH" ] && [ -s "$TRACE_PATH" ]; then
  LINES=$(wc -l < "$TRACE_PATH" | tr -d ' ')
  if [ "$LINES" -ge 3 ]; then
    pass "trace persistence (finalize_run)"
  else
    fail "trace persistence (finalize_run)"
  fi
else
  fail "trace persistence (finalize_run)"
fi

echo ""
echo "==========================="
echo "✅ Passed: $PASS"
echo "❌ Failed: $FAIL"
echo ""

if [ "$FAIL" -ne 0 ]; then
  echo "❌ Run structure validation FAILED"
  exit 1
fi

echo "🎉 Run structure validation passed"