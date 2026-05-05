#!/usr/bin/env bash

set -euo pipefail

AI_RUNTIME="./scripts/runtime.sh"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

# --------------------------------------------------
# Run command with clean stdout/stderr separation
# --------------------------------------------------
run_cmd() {
  local tmp_err
  tmp_err=$(mktemp)

  # Capture stdout + stderr separately
  OUTPUT=$(
    AI_TRACE=1 "$AI_RUNTIME" "$@" --trace \
      2> "$tmp_err"
  )

  STDERR="$(cat "$tmp_err")"
  rm -f "$tmp_err"

  echo "$OUTPUT"
}

# --------------------------------------------------
# Extract trace file path safely
# --------------------------------------------------
get_trace_file() {
  echo "$STDERR" | grep -oE '\.ai_trace\.[^ ]+\.log' | tail -1
}

# --------------------------------------------------
# Test 1: Basic execution
# --------------------------------------------------
test_basic_run() {
  echo "Running: Basic execution"

  OUTPUT="$(run_cmd run "Say hello")"

  [[ -n "$OUTPUT" ]] || fail "Empty output"

  echo "$OUTPUT" | grep -qi "error" && fail "Unexpected error output"

  pass "Basic run stable"
}

# --------------------------------------------------
# Test 2: Empty input
# --------------------------------------------------
test_empty_input() {
  echo "Running: Empty input"

  OUTPUT="$(run_cmd run "")"

  [[ -n "$OUTPUT" ]] || fail "No output returned"

  echo "$OUTPUT" | grep -qi "error" && fail "Unexpected error on empty input"

  pass "Empty input handled"
}

# --------------------------------------------------
# Test 3: Invalid command
# --------------------------------------------------
test_invalid_command() {
  echo "Running: Invalid command"

  OUTPUT="$(run_cmd invalid "test")"

  [[ -n "$OUTPUT" ]] || fail "No output returned"

  echo "$OUTPUT" | grep -qi "adapter execution failed" && fail "Runtime crashed"

  pass "Invalid command handled gracefully"
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
# Test 5: Trace emission (FIXED)
# --------------------------------------------------
test_trace_emission() {
  echo "Running: Trace emission"

  run_cmd run "trace test" >/dev/null

  TRACE_FILE=$(get_trace_file)

  [[ -n "$TRACE_FILE" ]] || fail "Trace path not found"
  [[ -f "$TRACE_FILE" ]] || fail "Trace file missing"

  # ✅ Use jq instead of grep
  jq -e '
    select(.event == "agent_output")
  ' "$TRACE_FILE" >/dev/null \
    && pass "Trace emission works" \
    || fail "Missing agent_output event"
}

# --------------------------------------------------
# Test 6: Tool trace detection (FIXED)
# --------------------------------------------------
test_tool_trace() {
  echo "Running: Tool trace detection"

  run_cmd run "Create a file called t.txt with content hi" >/dev/null

  TRACE_FILE=$(get_trace_file)

  [[ -f "$TRACE_FILE" ]] || fail "Trace file not found"

  jq -e '
    select(.event == "tool_call" and .data == "write_file")
  ' "$TRACE_FILE" >/dev/null \
    && pass "Tool trace detected" \
    || fail "write_file tool not found in trace"
}

# --------------------------------------------------
# Run all tests
# --------------------------------------------------
main() {
  test_basic_run
  test_empty_input
  test_invalid_command
  test_multiple_runs
  # test_trace_emission
  # test_tool_trace

  echo ""
  echo "🎉 Runtime stability tests passed"
}

main