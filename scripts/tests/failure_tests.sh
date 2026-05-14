#!/usr/bin/env bash
###################################################################
# failure_tests.sh — Runtime Failure Path Validation Suite
#
# Validates:
# - invalid adapter handling
# - malformed JSON handling
# - invalid contract handling
# - timeout handling
# - missing command handling
# - trace integrity on failure
#
# Usage:
#   ./scripts/tests/failure_tests.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"
ADAPTER_DIR="${ROOT_DIR}/scripts/adapters"

PASS_COUNT=0
FAIL_COUNT=0

TEST_TMP_DIR="$(
  mktemp -d "${ROOT_DIR}/tmp/tests/failure.XXXXXX"
)"

mkdir -p "$TEST_TMP_DIR"

cleanup() {
  rm -rf "$TEST_TMP_DIR"
}

trap cleanup EXIT

# ================================================================
# Helpers
# ================================================================

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

# ================================================================
# 1️⃣ Missing command
# ================================================================

test_missing_command() {

  output=$("$RUNTIME" 2>&1 || true)

  echo "$output" | grep -qi "usage"
}

# ================================================================
# 2️⃣ Missing adapter
# ================================================================

test_missing_adapter() {

  output=$(
    AI_ADAPTER=does_not_exist \
    "$RUNTIME" run "hello" 2>&1 || true
  )

  echo "$output" | grep -qi "adapter not found"
}

# ================================================================
# 3️⃣ Invalid JSON from adapter
# ================================================================

test_invalid_json_adapter() {

  BAD_ADAPTER="${ADAPTER_DIR}/bad_json.sh"

  cat > "$BAD_ADAPTER" <<'EOF'
#!/usr/bin/env bash
echo 'this is not json'
EOF

  chmod +x "$BAD_ADAPTER"

  output=$(
    AI_ADAPTER=bad_json \
    "$RUNTIME" run "hello" 2>&1 || true
  )

  rm -f "$BAD_ADAPTER"

  echo "$output" | jq -e '
    .status == "error" and
    (.output | contains("Invalid runtime JSON"))
  ' >/dev/null
}

# ================================================================
# 4️⃣ Invalid adapter contract
# ================================================================

test_invalid_contract() {

  BAD_ADAPTER="${ADAPTER_DIR}/bad_contract.sh"

  cat > "$BAD_ADAPTER" <<'EOF'
#!/usr/bin/env bash
echo '{"foo":"bar"}'
EOF

  chmod +x "$BAD_ADAPTER"

  output=$(
    AI_ADAPTER=bad_contract \
    "$RUNTIME" run "hello" 2>&1 || true
  )

  rm -f "$BAD_ADAPTER"

  echo "$output" | jq -e '
    .status == "error" and
    (.output | contains("Invalid adapter contract"))
  ' >/dev/null
}

# ================================================================
# 5️⃣ Adapter timeout
# ================================================================

test_timeout() {

  BAD_ADAPTER="${ADAPTER_DIR}/timeout_adapter.sh"

  cat > "$BAD_ADAPTER" <<'EOF'
#!/usr/bin/env bash
sleep 10
echo '{"status":"done","output":"late","meta":{}}'
EOF

  chmod +x "$BAD_ADAPTER"

  output=$(
    AI_TIMEOUT=1 \
    AI_ADAPTER=timeout_adapter \
    "$RUNTIME" run "hello" 2>&1 || true
  )

  rm -f "$BAD_ADAPTER"

  echo "$output" | grep -Eqi \
    "Invalid runtime JSON|timed out|terminated"
}

# ================================================================
# 6️⃣ Trace emitted on failure
# ================================================================

test_trace_failure_integrity() {

  BAD_ADAPTER="${ADAPTER_DIR}/trace_fail.sh"

  cat > "$BAD_ADAPTER" <<'EOF'
#!/usr/bin/env bash
echo '{"status":"bad"}'
EOF

  chmod +x "$BAD_ADAPTER"

  mkdir -p "$TEST_TMP_DIR"

  STDERR_FILE="${TEST_TMP_DIR}/stderr.log"

  AI_TRACE=1 \
  AI_ADAPTER=trace_fail \
  "$RUNTIME" run "hello" \
    > /dev/null \
    2> "$STDERR_FILE" || true

  TRACE_FILE=$(
    grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
      "$STDERR_FILE" \
      | tail -1
  )

  rm -f "$BAD_ADAPTER"

  test -n "${TRACE_FILE:-}" &&
  test -f "$TRACE_FILE"
}

# ================================================================
# 🚀 Run Tests
# ================================================================

echo ""
echo "🧪 Runtime Failure Path Suite"
echo "=============================="
echo ""

run_test "Missing command" test_missing_command
run_test "Missing adapter" test_missing_adapter
run_test "Invalid JSON adapter" test_invalid_json_adapter
run_test "Invalid adapter contract" test_invalid_contract
run_test "Adapter timeout" test_timeout
run_test "Trace integrity on failure" test_trace_failure_integrity

echo ""
echo "=============================="
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo "❌ Failure-path validation FAILED"
  exit 1
fi

echo "🎉 Failure-path validation passed"