#!/usr/bin/env bash
###################################################################
# runtime_eval_ledger_tests.sh
#
# Phase 3.6D Runtime Eval-from-Ledger Validation Suite
#
# Validates:
# - default trace-based evaluation
# - optional ledger-based evaluation
# - trace/ledger evaluation parity
# - deterministic missing-ledger behavior
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Eval Ledger Validation"
echo "=================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_eval_ledger_test.py; then
  echo "✅ Runtime eval-ledger test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime eval-ledger test"
  FAILED=$((FAILED + 1))
fi

echo
echo "=================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime eval-ledger validation failed"
  exit 1
fi

echo
echo "🎉 Runtime eval-ledger validation passed"
