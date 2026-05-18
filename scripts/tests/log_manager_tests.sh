#!/usr/bin/env bash
###################################################################
# log_manager_tests.sh
#
# Log Manager Safety + Cleanup Validation
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PASSED=0
FAILED=0

pass() {
  echo "✅ $1"
  PASSED=$((PASSED + 1))
}

fail() {
  echo "❌ $1"
  FAILED=$((FAILED + 1))
}

run_case() {
  local name="$1"
  shift

  if "$@"; then
    pass "$name"
  else
    fail "$name"
  fi
}

case_unittest_suite() {
  python3 -m unittest discover -s scripts/maintenance -p "log_manager_test.py"
}

echo ""
echo "🧪 Log Manager Validation"
echo "========================="

run_case "python log_manager unittest suite" case_unittest_suite

echo ""
echo "========================="
echo "✅ Passed: ${PASSED}"
echo "❌ Failed: ${FAILED}"

if [ "${FAILED}" -ne 0 ]; then
  echo ""
  echo "❌ Log manager validation failed"
  exit 1
fi

echo ""
echo "🎉 Log manager validation passed"
