#!/usr/bin/env bash
###################################################################
# runtime_ledger_canary_tests.sh
#
# Phase 3.8A Runtime Ledger Canary Validation Suite
#
# Validates:
# - explicit canary mode enablement
# - authoritative/parity canary compatibility
# - canary readiness aggregation
# - canary CLI behavior and strict semantics
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Canary Validation"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_canary_test.py; then
  echo "✅ Runtime ledger canary tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger canary tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger canary validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger canary validation passed"
