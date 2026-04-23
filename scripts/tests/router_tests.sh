#!/usr/bin/env bash

set -euo pipefail

ROUTER="./scripts/router.sh"

pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; exit 1; }

# --------------------------------------------------
# Helper: validate JSON
# --------------------------------------------------
is_json() {
  echo "$1" | jq -e . >/dev/null 2>&1
}

# --------------------------------------------------
# Test 1: Basic success (LiteLLM path)
# --------------------------------------------------
test_litellm_success() {
  echo "Running: LiteLLM success"

  RESPONSE="$($ROUTER run "Say hello")"

  is_json "$RESPONSE" || fail "Invalid JSON"

  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  [[ "$STATUS" == "done" || "$STATUS" == "continue" ]] \
    && pass "LiteLLM success" \
    || fail "Unexpected status: $STATUS"
}

# --------------------------------------------------
# Test 2: Forced fallback (break LiteLLM)
# --------------------------------------------------
test_fallback_to_mock() {
  echo "Running: Fallback to mock"

  # Force guaranteed connection failure (closed port)
  export LITELLM_BASE_URL="http://127.0.0.1:9"

  RESPONSE="$($ROUTER run "Hello fallback")"

  unset LITELLM_BASE_URL

  is_json "$RESPONSE" || fail "Invalid JSON"

  OUTPUT=$(echo "$RESPONSE" | jq -r '.output')

  echo "$OUTPUT" | grep -q "\[MOCK" \
    && pass "Fallback triggered" \
    || fail "Did not fallback to mock"
}

# --------------------------------------------------
# Test 3: Always returns output
# --------------------------------------------------
test_non_empty_output() {
  echo "Running: Non-empty output"

  RESPONSE="$($ROUTER run "")"

  OUTPUT=$(echo "$RESPONSE" | jq -r '.output')

  [[ -n "$OUTPUT" ]] \
    && pass "Non-empty output" \
    || fail "Empty output detected"
}

# --------------------------------------------------
# Test 4: Invalid command handling
# --------------------------------------------------
test_invalid_command() {
  echo "Running: Invalid command"

  RESPONSE="$($ROUTER invalid "test" || true)"

  is_json "$RESPONSE" || fail "Invalid JSON"

  STATUS=$(echo "$RESPONSE" | jq -r '.status')

  [[ "$STATUS" == "error" ]] \
    && pass "Invalid command handled" \
    || fail "Expected error status"
}

# --------------------------------------------------
# Test 5: JSON integrity under stress
# --------------------------------------------------
test_multiple_runs() {
  echo "Running: Multiple sequential runs"

  for i in {1..5}; do
    RESPONSE="$($ROUTER run "Test $i")"
    is_json "$RESPONSE" || fail "Run $i returned invalid JSON"
  done

  pass "Multiple runs stable"
}

# --------------------------------------------------
# Run all tests
# --------------------------------------------------
main() {
  test_litellm_success
  test_fallback_to_mock
  test_non_empty_output
  test_invalid_command
  test_multiple_runs

  echo ""
  echo "🎉 All router tests passed"
}

main