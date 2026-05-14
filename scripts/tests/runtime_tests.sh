#!/usr/bin/env bash
###################################################################
# runtime_tests.sh
#
# Phase 3 Runtime Validation Suite
#
# Validates:
# ✅ external response contract
# ✅ schema_version propagation
# ✅ typed metadata integrity
# ✅ NDJSON replay compatibility
# ✅ runtime trace lifecycle
# ✅ tool trace emission
# ✅ deterministic response envelopes
# ✅ sequential runtime stability
#
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AI_RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

# Runtime validation should be deterministic and offline-safe.
# Adapter-specific suites should test agent/goose/litellm separately.
export AI_ADAPTER="mock"

PASS_COUNT=0
FAIL_COUNT=0

OUTPUT=""
STDERR=""

# ===============================================================
# 🧹 Temp workspace
# ===============================================================

TEST_TMP_DIR="${ROOT_DIR}/tmp/tests"

mkdir -p "$TEST_TMP_DIR"

cleanup() {
  rm -f "${TEST_TMP_DIR}"/* 2>/dev/null || true
}

trap cleanup EXIT

# ===============================================================
# Helpers
# ===============================================================

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

# ---------------------------------------------------------------
# Run runtime safely
# ---------------------------------------------------------------

run_cmd() {

  local tmp_err

  tmp_err=$(mktemp)

  set +e
  OUTPUT=$(
    AI_TRACE=1 \
    "$AI_RUNTIME" "$@" --trace \
      2> "$tmp_err"
  )
  local exit_code=$?
  set -e

  STDERR="$(cat "$tmp_err")"

  rm -f "$tmp_err"
}

# ---------------------------------------------------------------
# Extract trace path
# ---------------------------------------------------------------

extract_trace_file() {

  echo "$STDERR" \
    | grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    | tail -1
}

# ===============================================================
# Test 1: Response schema contract
# ===============================================================

test_response_contract() {

  echo "Running: Response schema contract"

  run_cmd run "Say hello"

  echo "$OUTPUT" | jq -e '
    .schema_version == 1 and
    (.status == "done" or .status == "error") and
    (.meta | has("run_id")) and
    (.meta | has("run_path")) and
    (.meta | has("error")) and
    (.meta.error | type == "boolean")
  ' >/dev/null \
    || {
      fail "Invalid response contract"
      return
    }

  pass "Response schema valid"
}

# ===============================================================
# Test 2: Empty input handling
# ===============================================================

test_empty_input() {

  echo "Running: Empty input"

  run_cmd run ""

  echo "$OUTPUT" | jq -e '
    .status and
    .meta
  ' >/dev/null \
    || {
      fail "Empty input invalid"
      return
    }

  pass "Empty input handled"
}

# ===============================================================
# Test 3: Invalid command rejection
# ===============================================================

test_invalid_command() {

  echo "Running: Invalid command"

  run_cmd invalid "test"

  echo "$OUTPUT" | jq -e '
    .status == "error"
  ' >/dev/null \
    || {
      fail "Invalid command not rejected"
      return
    }

  pass "Invalid command handled"
}

# ===============================================================
# Test 4: Sequential stability
# ===============================================================

test_multiple_runs() {

  echo "Running: Sequential runs"

  for i in {1..5}; do

    run_cmd run "Say hello $i"

    echo "$OUTPUT" | jq -e '
      .status == "done"
    ' >/dev/null \
      || {
        fail "Sequential run failure"
        return
      }

  done

  pass "Sequential runs stable"
}

# ===============================================================
# Test 5: Trace emission
# ===============================================================

test_trace_emission() {

  echo "Running: Trace emission"

  run_cmd run \
    "Create a file called ${TEST_TMP_DIR}/trace.txt with content hi"

  TRACE_FILE=$(extract_trace_file)

  test -n "${TRACE_FILE:-}" \
    || {
      fail "Trace path missing"
      return
    }

  test -f "$TRACE_FILE" \
    || {
      fail "Trace file missing"
      return
    }

  jq -s -e '
    any(.[]; .event == "tool_call")
  ' "$TRACE_FILE" >/dev/null \
    || {
      fail "tool_call missing"
      return
    }

  pass "Trace emission works"
}

# ===============================================================
# Test 6: Tool trace detection
# ===============================================================

test_tool_trace() {

  echo "Running: Tool trace detection"

  run_cmd run \
    "Create a file called ${TEST_TMP_DIR}/tool.txt with content hi"

  TRACE_FILE=$(extract_trace_file)

  test -f "$TRACE_FILE" \
    || {
      fail "Trace file not found"
      return
    }

  jq -s -e '
    any(
      .[];
      .event == "tool_call" and
      .data == "write_file"
    )
  ' "$TRACE_FILE" >/dev/null \
    || {
      fail "write_file tool trace missing"
      return
    }

  jq -s -e '
    any(
      .[];
      .event == "tool_result" and
      .data == "write_file"
    )
  ' "$TRACE_FILE" >/dev/null \
    || {
      fail "write_file tool result missing"
      return
    }

  pass "Tool trace lifecycle valid"
}

# ===============================================================
# Test 7: Trace schema versioning
# ===============================================================

test_trace_schema_version() {

  echo "Running: Trace schema versioning"

  run_cmd run "Say hello"

  TRACE_FILE=$(extract_trace_file)

  test -f "$TRACE_FILE" \
    || {
      fail "Trace file missing"
      return
    }

  jq -s -e '
    all(
      .[];
      .schema_version == 1
    )
  ' "$TRACE_FILE" >/dev/null \
    || {
      fail "Trace schema_version missing"
      return
    }

  pass "Trace schema version valid"
}

# ===============================================================
# Test 8: Lifecycle integrity
# ===============================================================

test_lifecycle_integrity() {

  echo "Running: Lifecycle integrity"

  run_cmd run "Say hello"

  TRACE_FILE=$(extract_trace_file)

  FIRST_EVENT=$(
    head -n 1 "$TRACE_FILE" \
      | jq -r '.event'
  )

  LAST_EVENT=$(
    tail -n 1 "$TRACE_FILE" \
      | jq -r '.event'
  )

  [[ "$FIRST_EVENT" == "session_start" ]] \
    || {
      fail "session_start missing"
      return
    }

  [[ "$LAST_EVENT" == "session_end" ]] \
    || {
      fail "session_end missing"
      return
    }

  pass "Lifecycle ordering valid"
}

# ===============================================================
# Test 9: Replay compatibility
# ===============================================================

test_replay_compatibility() {

  echo "Running: Replay compatibility"

  run_cmd run "Say hello"

  TRACE_FILE=$(extract_trace_file)

  python3 - <<PY >/dev/null
from runtime.replay import replay_trace
replay_trace("${TRACE_FILE}")
PY

  if [ $? -eq 0 ]; then
    pass "Replay compatibility valid"
  else
    fail "Replay compatibility failed"
  fi
}

# ===============================================================
# Run suite
# ===============================================================

main() {

  echo ""
  echo "🧪 Runtime Validation Suite (Phase 3)"
  echo "====================================="
  echo ""

  test_response_contract
  test_empty_input
  test_invalid_command
  test_multiple_runs
  test_trace_emission
  test_tool_trace
  test_trace_schema_version
  test_lifecycle_integrity
  test_replay_compatibility

  echo ""
  echo "====================================="
  echo "✅ Passed: $PASS_COUNT"
  echo "❌ Failed: $FAIL_COUNT"
  echo ""

  if [ "$FAIL_COUNT" -ne 0 ]; then
    echo "❌ Runtime validation FAILED"
    exit 1
  fi

  echo "🎉 Runtime validation passed"
}

main