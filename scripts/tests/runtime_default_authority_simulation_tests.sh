#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "🧪 Runtime Default Authority Simulation"
echo "========================================"

if python3 -m unittest runtime/tests/runtime_default_authority_simulation_test.py; then
  echo "✅ Runtime default authority simulation tests"
  echo ""
  echo "========================================"
  echo "✅ Passed: 1"
  echo "❌ Failed: 0"
  echo ""
  echo "🎉 Runtime default authority simulation validation passed"
else
  echo "❌ Runtime default authority simulation tests failed"
  exit 1
fi
