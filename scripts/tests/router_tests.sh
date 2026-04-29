#!/usr/bin/env bash

set -euo pipefail

AI_RUNTIME="./scripts/runtime.sh"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

# --------------------------------------------------
# Helper: safe execution
# --------------------------------------------------
run_cmd() {
  "$AI_RUNTIME" "$@" 2>&1
}

# --------------------------------------------------
# Test 1: Basic execution stability
# --------------------------------------------------
test_basic_run() {
  echo "Running: Basic execution"

  OUTPUT="$(run_cmd run "Say hello")"

  [[ -n "$OUTPUT" ]] || fail "Empty output"

  echo "$OUTPUT" | grep -qi "error" && fail "Unexpected error output"

  pass "Basic run stable"
}

# --------------------------------------------------
# Test 2: Runtime does not crash on empty input
# --------------------------------------------------
test_empty_input() {
  echo "Running: Empty input"

  OUTPUT="$(run_cmd run "")"

  [[ -n "$OUTPUT" ]] || fail "No output returned"

  pass "Empty input handled"
}

# --------------------------------------------------
# Test 3: Invalid command handling (non-zero exit expected)
# --------------------------------------------------
test_invalid_command() {
  echo "Running: Invalid command"

  set +e
  OUTPUT="$($AI_RUNTIME invalid "test" 2>&1)"
  EXIT_CODE=$?
  set -e

  [[ $EXIT_CODE -ne 0 ]] || fail "Expected failure exit code"

  echo "$OUTPUT" | grep -qi "Usage" \
    && pass "Invalid command handled" \
    || fail "Expected usage message"
}

# --------------------------------------------------
# Test 4: Sequential stability
# --------------------------------------------------
test_multiple_runs() {
  echo "Running: Sequential runs"

  for i in {1..5}; do
    OUTPUT="$(run_cmd run "Test $i")"
    [[ -n "$OUTPUT" ]] || fail "Run $i returned empty output"
  done

  pass "Multiple runs stable"
}

# --------------------------------------------------
# Run all tests
# --------------------------------------------------
main() {
  test_basic_run
  test_empty_input
  test_invalid_command
  test_multiple_runs

  echo ""
  echo "🎉 Runtime stability tests passed"
}

main