#!/usr/bin/env bash
###################################################################
# runtime_dual_authority_validation_tests.sh
#
# Phase 3.9C Dual-Authority Validation Window
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Dual-Authority Validation"
echo "======================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_dual_authority_validation_test.py; then
  echo "✅ Runtime dual-authority validation tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime dual-authority validation tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "======================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime dual-authority validation failed"
  exit 1
fi

echo
echo "🎉 Runtime dual-authority validation passed"
