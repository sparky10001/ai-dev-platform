#!/usr/bin/env bash
###################################################################
# runtime_run_lifecycle_tests.sh
#
# Phase 3.5 Runtime Lifecycle Validation Suite
#
# Validates:
# - runtime run initialization
# - session_start lifecycle transition
# - agent_output lifecycle transition
# - session_end lifecycle transition
# - failure lifecycle handling
# - deterministic response envelope construction
# - lifecycle contract stability
#
# Purpose:
# - protects lifecycle extraction from regressions
# - ensures lifecycle transitions remain replay-safe
# - preserves runtime behavior during decomposition
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Lifecycle Validation"
echo "==============================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_run_lifecycle_test.py; then
  echo "✅ Runtime lifecycle test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime lifecycle test"
  FAILED=$((FAILED + 1))
fi

echo
echo "==============================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo
  echo "❌ Runtime lifecycle validation failed"
  exit 1
fi

echo
echo "🎉 Runtime lifecycle validation passed"