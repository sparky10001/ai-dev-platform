#!/usr/bin/env bash
###################################################################
# runtime_authority_policy_tests.sh
#
# Phase 3.9B Runtime Authority Policy Validation Suite
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Authority Policy Validation"
echo "========================================"

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_authority_policy_test.py; then
  echo "✅ Runtime authority policy tests"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime authority policy tests"
  FAILED=$((FAILED + 1))
fi

echo
echo "========================================"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ "$FAILED" -ne 0 ]; then
  echo
  echo "❌ Runtime authority policy validation failed"
  exit 1
fi

echo
echo "🎉 Runtime authority policy validation passed"
