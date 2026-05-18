#!/usr/bin/env bash
###################################################################
# runtime_scenario_runner_tests.sh
#
# Phase 3.6 Runtime Scenario Runner Validation Suite
#
# Validates:
# - runtime scenario runner bounded execution
# - model argument compatibility
# - deterministic mock scenario execution
# - real agent tool scenario execution
# - clean invalid-scenario failure handling
# - timeout configuration validation
# - evaluator criteria regression protection
#
# Purpose:
# - protects runtime_run_scenario.sh compatibility
# - ensures scenario runner does not hang
# - validates mock/agent scenario parity for basic filesystem workflows
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCENARIO_RUNNER="$ROOT_DIR/scripts/runtime_run_scenario.sh"
SCENARIO="$ROOT_DIR/scenarios/tests/test_list_files_v3.json"

TEST_FILE="tmp/runtime_scenario_runner_${$}.txt"
trap 'rm -f "$TEST_FILE" tmp/hello.txt hello.txt' EXIT
rm -f "$TEST_FILE" tmp/hello.txt hello.txt

PASSED=0
FAILED=0

pass() {
  echo "✅ $1"
  PASSED=$((PASSED + 1))
}

fail() {
  echo "❌ $1"
  FAILED=$((FAILED + 1))
}

run_case() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

run_capture() {
  local out="$1"
  shift

  set +e
  "$@" >"$out" 2>&1
  local rc=$?
  set -e

  return "$rc"
}

case_fast_model_completes_or_fails_cleanly() {
  local out
  out="$(mktemp)"

  set +e
  timeout 35 "$SCENARIO_RUNNER" "$SCENARIO" --model=fast >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -eq 124 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  grep -Eq "(🧪 Evaluation:|Scenario runtime failed|Scenario runtime timed out)" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

case_mock_scenario_passes() {
  local out
  out="$(mktemp)"

  set +e
  AI_ADAPTER=mock timeout 35 "$SCENARIO_RUNNER" "$SCENARIO" --model=fast >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  grep -q "🎯 SCORE: 1" "$out" && grep -q "✅ Scenario passed" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

case_agent_scenario_passes() {
  local out
  out="$(mktemp)"

  set +e
  AI_ADAPTER=agent timeout 35 "$SCENARIO_RUNNER" "$SCENARIO" --model=fast >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -ne 0 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  grep -q "🎯 SCORE: 1" "$out" && grep -q "✅ Scenario passed" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

case_invalid_path_fails_cleanly() {
  local out
  out="$(mktemp)"

  set +e
  "$SCENARIO_RUNNER" "$ROOT_DIR/scenarios/tests/does_not_exist.json" >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -eq 0 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  grep -q "Scenario not found" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

case_timeout_config_path_fails_cleanly() {
  local out
  out="$(mktemp)"

  set +e
  SCENARIO_TIMEOUT=0 "$SCENARIO_RUNNER" "$SCENARIO" --model=fast >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -eq 0 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  grep -q "SCENARIO_TIMEOUT must be a positive integer" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

case_no_empty_criteria_regression() {
  local out
  out="$(mktemp)"

  set +e
  AI_ADAPTER=mock timeout 35 "$SCENARIO_RUNNER" "$SCENARIO" --model=fast >"$out" 2>&1
  local rc=$?
  set -e

  if [ "$rc" -eq 124 ]; then
    cat "$out"
    rm -f "$out"
    return 1
  fi

  ! grep -q "Empty criteria" "$out"
  local ok=$?
  rm -f "$out"
  return "$ok"
}

echo ""
echo "🧪 Runtime Scenario Runner Validation"
echo "====================================="

run_case "list_files_v3 --model=fast completes or fails cleanly" case_fast_model_completes_or_fails_cleanly
run_case "list_files_v3 passes with AI_ADAPTER=mock" case_mock_scenario_passes
run_case "list_files_v3 passes with AI_ADAPTER=agent" case_agent_scenario_passes
run_case "invalid scenario path fails cleanly" case_invalid_path_fails_cleanly
run_case "scenario timeout config fails cleanly" case_timeout_config_path_fails_cleanly
run_case "no Empty criteria regression" case_no_empty_criteria_regression

echo
echo "====================================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo
  echo "❌ Runtime scenario runner validation failed"
  exit 1
fi

echo
echo "🎉 Runtime scenario runner validation passed"