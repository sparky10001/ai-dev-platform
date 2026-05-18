#!/usr/bin/env bash
###################################################################
# scripts/tests/mock_adapter_tool_simulation_tests.sh
#
# Phase 3.6I Mock Adapter Tool Simulation Validation
#
# Validates:
# - deterministic write_file/list_files simulation in AI_ADAPTER=mock
# - deterministic read_file simulation behavior
# - scenario runner compatibility under mock
# - no dependency on deprecated scripts/adapters/_base.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TEST_FILE="tmp/mock_adapter_tool_simulation_${$}.txt"
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

case_mock_ai_run_create_and_list() {
  local out base
  base="$(basename "$TEST_FILE")"
  out="$(AI_ADAPTER=mock ./ai run "Create a file called $TEST_FILE with content 'hi' and then list files")"

  echo "$out" | jq -e '.status == "done"' >/dev/null &&
  echo "$out" | jq -e '.meta.error == false' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.event == "tool_call" and .data == "write_file")) | length > 0' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.event == "tool_result" and .data == "write_file")) | length > 0' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.event == "tool_call" and .data == "list_files")) | length > 0' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.event == "tool_result" and .data == "list_files")) | length > 0' >/dev/null &&
  echo "$out" | jq -e --arg base "$base" '.meta.trace | map(select(.event == "tool_result" and .data == "list_files" and (.meta.result.files | index($base) != null))) | length > 0' >/dev/null
}

case_mock_scenario_passes() {
  local out rc tmp
  tmp="$(mktemp)"
  set +e
  AI_ADAPTER=mock ./scripts/runtime_run_scenario.sh scenarios/tests/test_list_files_v3.json --model=fast >"$tmp" 2>&1
  rc=$?
  set -e
  out="$(cat "$tmp")"
  rm -f "$tmp"

  [ "$rc" -eq 0 ] && (echo "$out" | grep -q "Scenario passed" || echo "$out" | grep -Eq "SCORE: 1(\.0+)?")
}

case_mock_list_files() {
  local out
  out="$(AI_ADAPTER=mock ./ai run "list files")"
  echo "$out" | jq -e '.status == "done"' >/dev/null &&
  echo "$out" | jq -e '.meta.error == false' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.data == "list_files")) | length >= 1' >/dev/null
}

case_no_base_dependency() {
  ! grep -q "_base.sh" scripts/adapters/mock.sh
}

case_mock_read_file() {
  local out
  out="$(AI_ADAPTER=mock ./ai run "read $(basename "$TEST_FILE")")"
  echo "$out" | jq -e '.status == "done"' >/dev/null &&
  echo "$out" | jq -e '.meta.trace | map(select(.event == "tool_call" and .data == "read_file")) | length > 0' >/dev/null
}

echo ""
echo "🧪 Mock Adapter Tool Simulation Validation"
echo "==========================================="

run_case "mock ai run simulates write_file+list_files" case_mock_ai_run_create_and_list
run_case "mock scenario list_files_v3 passes" case_mock_scenario_passes
run_case "mock list files uses tool trace" case_mock_list_files
run_case "mock adapter has no _base.sh dependency" case_no_base_dependency
run_case "mock read file deterministic handling" case_mock_read_file

echo ""
echo "==========================================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo ""
  echo "❌ Mock adapter tool simulation validation failed"
  exit 1
fi

echo ""
echo "🎉 Mock adapter tool simulation validation passed"
