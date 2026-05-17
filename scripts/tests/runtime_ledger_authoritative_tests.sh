#!/usr/bin/env bash
###################################################################
# runtime_ledger_authoritative_tests.sh
#
# Phase 3.6F Runtime Ledger-Authoritative Validation Suite
#
# Validates:
# - authoritative default switching
# - explicit source override behavior
# - parity enforcement
# - trace compatibility preservation
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Ledger Authoritative Validation"
echo "==========================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_ledger_authoritative_test.py; then
  echo "✅ Runtime ledger-authoritative test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime ledger-authoritative test"
  FAILED=$((FAILED + 1))
fi

echo
echo "==========================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime ledger-authoritative validation failed"
  exit 1
fi

echo
echo "🎉 Runtime ledger-authoritative validation passed"
