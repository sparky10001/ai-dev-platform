#!/usr/bin/env bash
###################################################################
# runtime_trace_pipeline_tests.sh
#
# Phase 3.5 Runtime Trace Pipeline Validation Suite
#
# Validates:
# - append-only NDJSON trace persistence
# - deterministic trace event normalization
# - replay-safe trace loading
# - streaming trace event iteration
# - tolerant malformed trace handling
# - strict-mode trace validation
# - run_id consistency validation
# - lifecycle ordering validation
#
# Purpose:
# - protects trace pipeline extraction from regressions
# - ensures trace ingestion remains replay-safe
# - preserves NDJSON and runtime behavior during decomposition
###################################################################

set -euo pipefail

echo ""
echo "🧪 Runtime Trace Pipeline Validation"
echo "===================================="

PASSED=0
FAILED=0

if python3 -m unittest runtime/tests/runtime_trace_pipeline_test.py; then
  echo "✅ Runtime trace pipeline test"
  PASSED=$((PASSED + 1))
else
  echo "❌ Runtime trace pipeline test"
  FAILED=$((FAILED + 1))
fi

echo
echo "===================================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo
  echo "❌ Runtime trace pipeline validation failed"
  exit 1
fi

echo
echo "🎉 Runtime trace pipeline validation passed"