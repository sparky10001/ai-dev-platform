#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AI_RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

OUTPUT=""
STDERR=""

# ---------------------------------------------------------------
# 🧹 Temp test workspace
# ---------------------------------------------------------------
TEST_TMP_DIR="${ROOT_DIR}/tmp/tests"
mkdir -p "$TEST_TMP_DIR"

cleanup() {
  rm -f "${TEST_TMP_DIR}"/* 2>/dev/null || true
}

trap cleanup EXIT

# --------------------------------------------------
# Run command safely
# --------------------------------------------------
run_cmd() {
  local tmp_err
  tmp_err=$(mktemp)

  OUTPUT=$(
    AI_TRACE=1 "$AI_RUNTIME" "$@" --trace \
      2> "$tmp_err"
  )

  STDERR="$(cat "$tmp_err")"

  rm -f "$tmp_err"
}

# --------------------------------------------------
# Extract latest trace file
# --------------------------------------------------
get_latest_trace() {
  find logs/traces -name "ai_trace.*.log" \
    | sort \
    | tail -1
}

# --------------------------------------------------
# Test 1: Basic execution
# --------------------------------------------------
test_basic_run() {
  echo "Running: Basic execution"

  run_cmd run "Say hello"

  echo "$OUTPUT" | jq -e '
    .status == "done"
  ' >/dev/null \
    || fail "Basic execution failed"

  pass "Basic run stable"
}

# --------------------------------------------------
# Test 2: Empty input
# --------------------------------------------------
test_empty_input() {
  echo "Running: Empty input"

  run_cmd run ""

  echo "$OUTPUT" | jq -e '
    .status
  ' >/dev/null \
    || fail "Invalid JSON response"

  pass "Empty input handled"
}

# --------------------------------------------------
# Test 3: Invalid command
# --------------------------------------------------
test_invalid_command() {
  echo "Running: Invalid command"

  run_cmd invalid "test"

  echo "$OUTPUT" | jq -e '
    .status == "error"
  ' >/dev/null \
    || fail "Invalid command not rejected"

  pass "Invalid command handled gracefully"
}

# --------------------------------------------------
# Test 4: Sequential stability
# --------------------------------------------------
test_multiple_runs() {
  echo "Running: Sequential runs"

  for i in {1..5}; do

    run_cmd run "Say hello $i"

    echo "$OUTPUT" | jq -e '
      .status == "done"
    ' >/dev/null \
      || fail "Run $i failed"

  done

  pass "Multiple runs stable"
}

# --------------------------------------------------
# Test 5: Trace emission
# --------------------------------------------------
test_trace_emission() {
  echo "Running: Trace emission"

  run_cmd run "Create a file called ${TEST_TMP_DIR}/trace.txt with content hi"

  TRACE_FILE=$(get_latest_trace)

  [[ -n "$TRACE_FILE" ]] \
    || fail "Trace path not found"

  [[ -f "$TRACE_FILE" ]] \
    || fail "Trace file missing"

  jq -s -e '
    map(select(.event == "tool_call")) | length > 0
  ' "$TRACE_FILE" >/dev/null \
    || fail "Missing tool_call event"

  pass "Trace emission works"
}

# --------------------------------------------------
# Test 6: Tool trace detection
# --------------------------------------------------
test_tool_trace() {
  echo "Running: Tool trace detection"

  run_cmd run \
    "Create a file called ${TEST_TMP_DIR}/t.txt with content hi"

  TRACE_FILE=$(get_latest_trace)

  [[ -f "$TRACE_FILE" ]] \
    || fail "Trace file not found"

  jq -s -e '
    map(
      select(
        .event == "tool_call"
        and .data == "write_file"
      )
    ) | length > 0
  ' "$TRACE_FILE" >/dev/null \
    || fail "write_file tool not found"

  pass "Tool trace detected"
}

# --------------------------------------------------
# Run all tests
# --------------------------------------------------
main() {

  test_basic_run
  test_empty_input
  test_invalid_command
  test_multiple_runs
  test_trace_emission
  test_tool_trace

  echo ""
  echo "🎉 Runtime stability tests passed"
}

main