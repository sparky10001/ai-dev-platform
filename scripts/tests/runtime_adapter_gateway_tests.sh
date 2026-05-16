#!/usr/bin/env bash
###################################################################
# runtime_adapter_gateway_tests.sh
#
# Phase 3.5 Runtime Adapter Gateway Validation Suite
#
# Validates:
# - adapter subprocess execution boundary
# - adapter stdout JSON parsing
# - adapter response normalization
# - adapter contract validation delegation
# - invalid JSON handling
# - timeout handling
# - deterministic adapter payload behavior
#
# Purpose:
# - protects adapter gateway extraction from regressions
# - ensures runtime adapter invocation remains contract-safe
# - preserves existing runtime behavior during decomposition
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Adapter Gateway Validation"
echo "====================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_adapter_gateway_test.py; then
  echo "✅ Runtime adapter gateway test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime adapter gateway test"
  FAILED=$((FAILED + 1))
fi

echo
echo "====================================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo
  echo "❌ Runtime adapter gateway validation failed"
  exit 1
fi

echo
echo "🎉 Runtime adapter gateway validation passed"