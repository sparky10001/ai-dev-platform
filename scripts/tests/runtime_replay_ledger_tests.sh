#!/usr/bin/env bash
###################################################################
# runtime_replay_ledger_tests.sh
#
# Phase 3.6C Runtime Replay-from-Ledger Validation Suite
#
# Validates:
# - trace replay remains default
# - optional replay loading from ledger
# - deterministic missing-ledger behavior
# - trace/ledger replay parity for dual-written runs
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Replay Ledger Validation"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_replay_ledger_test.py; then
  echo "✅ Runtime replay-ledger test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime replay-ledger test"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime replay-ledger validation failed"
  exit 1
fi

echo
echo "🎉 Runtime replay-ledger validation passed"
