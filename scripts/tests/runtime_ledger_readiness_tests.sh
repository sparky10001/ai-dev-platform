#!/usr/bin/env bash
###################################################################
# runtime_ledger_readiness_tests.sh
#
# Phase 3.6G Runtime Ledger Cutover Readiness Validation Suite
#
# Validates:
# - cutover readiness reporting
# - parity readiness
# - dependency audit structure
# - authoritative readiness state
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Readiness Validation"
echo "======================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_readiness_test.py; then
  echo "✅ Runtime ledger readiness test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger readiness test"
  FAILED=$((FAILED + 1))
fi

echo
echo "======================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger readiness validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger readiness validation passed"
