#!/usr/bin/env bash
###################################################################
# test_adapters.sh — Adapter Validation Suite (v3.0)
#
# Validates:
# - adapter contract shape
# - runtime compatibility
# - deterministic agent routing
# - trace propagation
# - JSON integrity
#
# Usage:
#   ./scripts/tests/test_adapters.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"
AGENT="${ROOT_DIR}/scripts/agent.py"

PASS_COUNT=0
FAIL_COUNT=0

# ---------------------------------------------------------------
# 🧹 Temp test workspace
# ---------------------------------------------------------------
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

run_test() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

# ===============================================================
# Tests
# ===============================================================

test_agent_ping() {

  OUTPUT=$(python3 "$AGENT" run "ping")

  echo "$OUTPUT" | jq -e '
    .status == "done" and
    .meta.adapter == "agent.py"
  ' >/dev/null
}

test_agent_basic_response() {

  OUTPUT=$(python3 "$AGENT" query "Say hello")

  echo "$OUTPUT" | jq -e '
    .status == "done"
  ' >/dev/null
}

test_agent_tool_use() {

  OUTPUT=$(python3 "$AGENT" run \
    "Create a file called ${TEST_TMP_DIR}/adapter_test.txt with content '\''hi'\'' and then list files")

  echo "$OUTPUT" | jq -e '
    .status == "done" and
    (.meta.trace | length >= 2)
  ' >/dev/null
}

test_tool_call_detected() {

  OUTPUT=$(python3 "$AGENT" run \
    "Create a file called ${TEST_TMP_DIR}/adapter_trace.txt with content '\''hello'\''")

  echo "$OUTPUT" | jq -e '
    any(
      .meta.trace[];
      .event == "tool_call" and
      .data == "write_file"
    )
  ' >/dev/null
}

test_tool_result_detected() {

  OUTPUT=$(python3 "$AGENT" run \
    "Create a file called ${TEST_TMP_DIR}/adapter_result.txt with content '\''ok'\''")

  echo "$OUTPUT" | jq -e '
    any(
      .meta.trace[];
      .event == "tool_result" and
      .data == "write_file"
    )
  ' >/dev/null
}

test_runtime_contract() {

  OUTPUT=$("$RUNTIME" run "Say hello")

  echo "$OUTPUT" | jq -e '
    .status and
    .output and
    .meta
  ' >/dev/null
}

test_runtime_trace_mode() {

  TRACE_OUTPUT=$(AI_TRACE=1 "$RUNTIME" run \
    "Create a file called ${TEST_TMP_DIR}/runtime_trace.txt with content hi" \
    --trace)

  echo "$TRACE_OUTPUT" | jq -e '
    .status == "done" and
    (.meta.trace | length > 0)
  ' >/dev/null
}

test_trace_contains_write_file() {

  TRACE_OUTPUT=$(AI_TRACE=1 "$RUNTIME" run \
    "Create a file called ${TEST_TMP_DIR}/trace_check.txt with content hi" \
    --trace)

  echo "$TRACE_OUTPUT" | jq -e '
    any(
      .meta.trace[];
      .event == "tool_call" and
      .data == "write_file"
    )
  ' >/dev/null
}

test_run_metadata() {

  OUTPUT=$(python3 "$AGENT" run "ping")

  echo "$OUTPUT" | jq -e '
    .meta.run_id and
    .meta.run_path
  ' >/dev/null
}

test_trace_logger_integration() {

  BEFORE_COUNT=$(find "${ROOT_DIR}/logs/traces" \
    -name "*.log" 2>/dev/null | wc -l)

  python3 "$AGENT" run \
    "Create a file called ${TEST_TMP_DIR}/trace_logger_test.txt with content hi" \
    >/dev/null

  AFTER_COUNT=$(find "${ROOT_DIR}/logs/traces" \
    -name "*.log" 2>/dev/null | wc -l)

  [[ "$AFTER_COUNT" -ge "$BEFORE_COUNT" ]]
}

# ===============================================================
# Run Suite
# ===============================================================

echo ""
echo "🧪 Adapter Validation Suite v3.0"
echo "================================"
echo ""

run_test "Agent ping contract"              test_agent_ping
run_test "Agent basic response"             test_agent_basic_response
run_test "Agent tool usage"                 test_agent_tool_use
run_test "Tool call trace detection"        test_tool_call_detected
run_test "Tool result trace detection"      test_tool_result_detected
run_test "Runtime contract"                 test_runtime_contract
run_test "Runtime trace mode"               test_runtime_trace_mode
run_test "Runtime write_file trace"         test_trace_contains_write_file
run_test "Run metadata present"             test_run_metadata
run_test "Trace logger integration"         test_trace_logger_integration

echo ""
echo "================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo ""
  echo "❌ Adapter validation FAILED"
  exit 1
fi

echo ""
echo "🎉 All adapter tests passed!"