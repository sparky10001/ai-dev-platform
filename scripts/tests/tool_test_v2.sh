#!/usr/bin/env bash
###################################################################
# test.sh — Full system validation harness (v1.2)
#
# Updates from v1.1:
# - Added a regression trap to test trace ndjson parsing
# - Added a full pipeline assertion (golden test)
#
# Usage:
#   ./scripts/test.sh
#   LITELLM_BASE_URL=http://litellm:4000 ./scripts/test.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXECUTOR="${ROOT_DIR}/scripts/tool_executor.py"
AGENT="${ROOT_DIR}/scripts/agent.py"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# ---------------------------------------------------------------
# 🧹 Cleanup — runs on exit (success or failure)
# ---------------------------------------------------------------
cleanup() {
  rm -f \
    "${ROOT_DIR}/.test_file.txt" \
    "${ROOT_DIR}/.test_write.txt" \
    2>/dev/null || true
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

skip() {
  echo "⏭️  $1 (skipped)"
  SKIP_COUNT=$((SKIP_COUNT+1))
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

# ---------------------------------------------------------------
# 🔍 Pre-checks
# ---------------------------------------------------------------
check_litellm() {
  local url="${LITELLM_BASE_URL:-http://litellm:4000}"
  curl -sf "${url}/health" -H "Authorization: Bearer ai-dev-platform" > /dev/null 2>&1
}

check_python() {
  command -v python3 > /dev/null 2>&1
}

check_jq() {
  command -v jq > /dev/null 2>&1
}

# ---------------------------------------------------------------
# 1️⃣ Tool Discovery (MCP)
# ---------------------------------------------------------------
test_tool_list() {
  output=$(python3 "$EXECUTOR" --list-tools)
  echo "$output" | jq empty >/dev/null 2>&1 &&
  echo "$output" | jq -e '.status == "done"' >/dev/null
}

# ---------------------------------------------------------------
# 2️⃣ Tool Discovery (OpenAI format)
# ---------------------------------------------------------------
test_tool_list_openai() {
  output=$(python3 "$EXECUTOR" --list-tools-openai)
  echo "$output" | jq empty >/dev/null 2>&1 &&
  echo "$output" | jq -e '.tools | length > 0' >/dev/null
}

# ---------------------------------------------------------------
# 3️⃣ Tool Execution (read_file)
# Fix v1.1: Use full path — resolves against BASE_DIR correctly
# ---------------------------------------------------------------
test_read_file() {
  local tmpfile="${ROOT_DIR}/.test_file.txt"
  echo "hello world" > "$tmpfile"

  # Use full absolute path — read_file.py resolves relative to BASE_DIR
  output=$(python3 "$EXECUTOR" read_file "{\"path\": \"${tmpfile}\"}")

  local result
  result=$(echo "$output" | jq -e '.status == "success"' >/dev/null 2>&1 \
    && echo "ok" || echo "fail")

  # Cleanup handled by trap — but remove early for cleanliness
  rm -f "$tmpfile"

  [ "$result" = "ok" ]
}

# ---------------------------------------------------------------
# 4️⃣ Tool Execution (write_file)
# Fix v1.1: Clean up artifact after test
# ---------------------------------------------------------------
test_write_file() {
  local outfile="${ROOT_DIR}/.test_write.txt"

  output=$(python3 "$EXECUTOR" write_file \
    "{\"path\": \".test_write.txt\", \"content\": \"ok\"}")

  local result
  if echo "$output" | jq -e '.status == "success"' >/dev/null 2>&1 \
     && [ -f "$outfile" ]; then
    result="ok"
  else
    result="fail"
  fi

  # Always clean up — trap also covers this on exit
  rm -f "$outfile"

  [ "$result" = "ok" ]
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
# 7️⃣ Tool Contract Validation (MCP shape)
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
# 8️⃣ OpenAI Schema Validation
# Verifies --list-tools-openai returns proper function format
# ---------------------------------------------------------------
test_openai_schema_shape() {
  output=$(python3 "$EXECUTOR" --list-tools-openai)

  echo "$output" | jq -e '
    .tools |
    length > 0 and
    all(
      .type == "function" and
      (.function | has("name")) and
      (.function | has("description")) and
      (.function | has("parameters"))
    )
  ' >/dev/null
}

# ---------------------------------------------------------------
# 9️⃣ Agent Basic Call
# Requires LiteLLM — skipped if not reachable
# ---------------------------------------------------------------
test_agent_basic() {
  output=$(python3 "$AGENT" query "Say hello")
  echo "$output" | jq -e '.status == "done"' >/dev/null
}

# ---------------------------------------------------------------
# 🔟 Agent Tool Call (integration)
# Requires LiteLLM — skipped if not reachable
# ---------------------------------------------------------------
test_agent_tool_use() {
  output=$(python3 "$AGENT" query "List files in current directory")
  echo "$output" | jq -e '.status == "done"' >/dev/null
}

# ---------------------------------------------------------------
# 1️⃣1️⃣ Runtime Integration
# Requires LiteLLM — skipped if not reachable
# ---------------------------------------------------------------
test_runtime() {
  output=$(bash "$RUNTIME" query "Say hello")
  test -n "$output"
}

# ---------------------------------------------------------------
# 1️⃣2️⃣ Evaluate Trace Tool
# ---------------------------------------------------------------
test_evaluate_trace() {
  local events='[{"event":"tool_call","step":1,"data":"read_file"}]'
  local criteria='[{"type":"tool_used","tool":"read_file"}]'

  output=$(python3 "$EXECUTOR" evaluate_trace \
    "{\"events\": ${events}, \"criteria\": ${criteria}}")

  echo "$output" | jq -e '
    .status == "success" and
    .data.score == 1 and
    .data.passed == 1 and
    .data.total == 1
  ' >/dev/null
}

# ---------------------------------------------------------------
# 1️⃣3️⃣ Test Trace NDJSON Parsing
# ---------------------------------------------------------------
test_trace_ndjson_parsing() {
  local trace='
{"event":"tool_call","data":"write_file"}
{"event":"tool_call","data":"list_files"}
'

  EVENTS=$(echo "$trace" | jq -s '.')

  echo "$EVENTS" | jq -e '
    length == 2 and
    .[0].event == "tool_call" and
    .[1].event == "tool_call"
  ' >/dev/null
}

# ---------------------------------------------------------------
# 1️⃣4️⃣ Test Full Pipeline
# ---------------------------------------------------------------
test_full_pipeline() {
  local input='{
    "events": [
      {"event":"tool_call","data":"write_file"},
      {"event":"tool_call","data":"list_files"}
    ],
    "criteria": [
      {"type":"tool_used","tool":"write_file"},
      {"type":"tool_used","tool":"list_files"}
    ]
  }'

  output=$(python3 "$EXECUTOR" evaluate_trace "$input")

  echo "$output" | jq -e '
    .data.score == 1 and
    .data.passed == 2
  ' >/dev/null
}

# ---------------------------------------------------------------
# 🚀 Run All Tests
# ---------------------------------------------------------------
echo ""
echo "🧪 AI Platform Test Suite v1.2"
echo "================================"
echo ""

# ---- Pre-checks ----
if ! check_python; then
  echo "❌ python3 not found — cannot run tests"
  exit 1
fi

if ! check_jq; then
  echo "❌ jq not found — cannot run tests"
  exit 1
fi

LITELLM_AVAILABLE=false
if check_litellm; then
  LITELLM_AVAILABLE=true
  echo "✅ LiteLLM reachable — all tests will run"
else
  echo "⚠️  LiteLLM not reachable — agent/runtime tests will be skipped"
fi
echo ""

# ---- Tool layer tests (no LiteLLM required) ----
echo "📦 Tool Layer"
echo "-------------"
run_test "Tool list (MCP)"         test_tool_list
run_test "Tool list (OpenAI)"      test_tool_list_openai
run_test "OpenAI schema shape"     test_openai_schema_shape
run_test "Tool contract shape"     test_contract_shape
run_test "read_file tool"          test_read_file
run_test "write_file tool"         test_write_file
run_test "list_files tool"         test_list_files
run_test "run_bash tool"           test_run_bash
run_test "evaluate_trace tool"     test_evaluate_trace
run_test "Trace NDJSON Parsing"    test_trace_ndjson_parsing
run_test "Test Full Pipeline"      test_full_pipeline

echo ""

# ---- Agent + runtime tests (require LiteLLM) ----
echo "🤖 Agent + Runtime Layer"
echo "------------------------"
if $LITELLM_AVAILABLE; then
  run_test "Agent basic response"  test_agent_basic
  run_test "Agent tool usage"      test_agent_tool_use
  run_test "Runtime integration"   test_runtime
else
  skip "Agent basic response"
  skip "Agent tool usage"
  skip "Runtime integration"
fi

echo ""
echo "================================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo "⏭️  Skipped: $SKIP_COUNT"

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo ""
  echo "❌ Test suite FAILED"
  exit 1
fi

echo ""
echo "🎉 All tests passed!"
