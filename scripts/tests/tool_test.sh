#!/usr/bin/env bash
###################################################################
# test.sh — Full system validation harness (v1.0)
#
# Validates:
# 1. Tool discovery (MCP + OpenAI schemas)
# 2. Individual tool execution
# 3. Tool contract compliance
# 4. Agent integration
# 5. Runtime integration
#
# Usage:
#   ./scripts/test.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXECUTOR="${ROOT_DIR}/scripts/tool_executor.py"
AGENT="${ROOT_DIR}/scripts/agent.py"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

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

# ---------------------------------------------------------------
# 🧪 Helpers
# ---------------------------------------------------------------
pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT+1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT+1))
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

json_valid() {
  jq empty >/dev/null 2>&1
}

# ---------------------------------------------------------------
# 1️⃣ Tool Discovery (MCP)
# ---------------------------------------------------------------
test_tool_list() {
  output=$(python3 "$EXECUTOR" --list-tools)
  echo "$output" | jq empty >/dev/null 2>&1
}

# ---------------------------------------------------------------
# 2️⃣ Tool Discovery (OpenAI format)
# ---------------------------------------------------------------
test_tool_list_openai() {
  output=$(python3 "$EXECUTOR" --list-tools-openai)
  echo "$output" | jq empty >/dev/null 2>&1
}

# ---------------------------------------------------------------
# 3️⃣ Tool Execution (read_file)
# ---------------------------------------------------------------
test_read_file() {
  tmpfile="${TEST_TMP_DIR}/.test_file.txt"
  echo "hello world" > "$tmpfile"

  output=$(python3 "$EXECUTOR" read_file \
  "{\"path\": \"${tmpfile}\"}")

  rm -f "$tmpfile"

  echo "$output" | jq empty >/dev/null 2>&1 &&
  echo "$output" | jq -e '.status == "success"' >/dev/null
}

# ---------------------------------------------------------------
# 4️⃣ Tool Execution (write_file)
# ---------------------------------------------------------------
test_write_file() {
  outfile="${TEST_TMP_DIR}/.test_write.txt"

  output=$(python3 "$EXECUTOR" write_file \
    "{\"path\": \"${outfile}\", \"content\": \"ok\"}")

  echo "$output" | jq -e '.status == "success"' >/dev/null &&
  test -f "$outfile"
}

# ---------------------------------------------------------------
# 5️⃣ Tool Execution (list_files)
# ---------------------------------------------------------------
test_list_files() {
  output=$(python3 "$EXECUTOR" list_files "{\"path\": \".\"}")

  echo "$output" | jq -e '.status == "success"' >/dev/null
}

# ---------------------------------------------------------------
# 6️⃣ Tool Execution (run_bash)
# ---------------------------------------------------------------
test_run_bash() {
  output=$(python3 "$EXECUTOR" run_bash "{\"command\": \"echo hi\"}")

  echo "$output" | jq -e '.status == "success"' >/dev/null
}

# ---------------------------------------------------------------
# 7️⃣ Tool Contract Validation
# ---------------------------------------------------------------
test_contract_shape() {
  output=$(python3 "$EXECUTOR" list_files "{\"path\": \".\"}")

  echo "$output" | jq -e '
    .status and
    (.status == "success" or .status == "error") and
    has("data") and
    has("error") and
    has("meta")
  ' >/dev/null
}

# ---------------------------------------------------------------
# 8️⃣ Agent Basic Call
# ---------------------------------------------------------------
test_agent_basic() {
  output=$(python3 "$AGENT" query "Say hello")

  echo "$output" | jq -e '.status == "done"' >/dev/null
}

# ---------------------------------------------------------------
# 9️⃣ Agent Tool Call (integration)
# ---------------------------------------------------------------
test_agent_tool_use() {
  output=$(python3 "$AGENT" query "List files in current directory")

  echo "$output" | jq -e '.status == "done"' >/dev/null
}

# ---------------------------------------------------------------
# 🔟 Runtime Integration
# ---------------------------------------------------------------
test_runtime() {
  output=$(bash "$RUNTIME" query "Say hello")

  test -n "$output"
}

# ---------------------------------------------------------------
# 🚀 Run All Tests
# ---------------------------------------------------------------
echo "🧪 Running AI Platform Tests..."
echo "--------------------------------"

run_test "Tool list (MCP)" test_tool_list
run_test "Tool list (OpenAI)" test_tool_list_openai
run_test "read_file tool" test_read_file
run_test "write_file tool" test_write_file
run_test "list_files tool" test_list_files
run_test "run_bash tool" test_run_bash
run_test "Tool contract shape" test_contract_shape
run_test "Agent basic response" test_agent_basic
run_test "Agent tool usage" test_agent_tool_use
run_test "Runtime integration" test_runtime

echo "--------------------------------"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"

if [ "$FAIL_COUNT" -ne 0 ]; then
  exit 1
fi

echo "🎉 All tests passed!"