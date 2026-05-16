#!/usr/bin/env bash
###################################################################
# runtime_event_ledger_tests.sh
#
# Phase 3.6A Runtime EventLedger Validation Suite
#
# Validates:
# - additive ledger writes
# - ledger NDJSON integrity
# - ledger validation
# - trace/ledger dual-write parity
# - strict ledger checks
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime EventLedger Validation"
echo "================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_event_ledger_test.py; then
  echo "✅ Runtime EventLedger test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime EventLedger test"
  FAILED=$((FAILED + 1))
fi

echo
echo "================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime EventLedger validation failed"
  exit 1
fi

echo
echo "🎉 Runtime EventLedger validation passed"
