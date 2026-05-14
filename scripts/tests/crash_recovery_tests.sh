#!/usr/bin/env bash
###################################################################
# crash_recovery_tests.sh
#
# Crash Recovery Validation Suite
#
# Validates:
# - trace durability during abrupt termination
# - partial trace persistence
# - replayability after crash
# - NDJSON integrity after interruption
# - orphaned run survivability
# - session_start durability
# - no malformed partial writes
#
# IMPORTANT:
# This intentionally kills live runtime processes.
#
# Usage:
#   ./scripts/tests/crash_recovery_tests.sh
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"
ADAPTER_DIR="${ROOT_DIR}/scripts/adapters"

PASS_COUNT=0
FAIL_COUNT=0

TMP_DIR="$(mktemp -d)"

cleanup() {

  rm -rf "$TMP_DIR"

  rm -f "${ADAPTER_DIR}/crash_sleep_adapter.sh" || true
}

trap cleanup EXIT

pass() {
  echo "✅ $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  echo "❌ $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

echo ""
echo "🧪 Crash Recovery Validation"
echo "============================"
echo ""

# ================================================================
# Create long-running adapter
# ================================================================

CRASH_ADAPTER="${ADAPTER_DIR}/crash_sleep_adapter.sh"

cat > "$CRASH_ADAPTER" <<'EOF'
#!/usr/bin/env bash

sleep 30

echo '{"status":"done","output":"finished","meta":{}}'
EOF

chmod +x "$CRASH_ADAPTER"

# ================================================================
# Launch runtime in background
# ================================================================

STDERR_FILE="${TMP_DIR}/stderr.log"
STDOUT_FILE="${TMP_DIR}/stdout.log"

AI_TRACE=1 \
AI_ADAPTER=crash_sleep_adapter \
"$RUNTIME" run "crash recovery test" \
  > "$STDOUT_FILE" \
  2> "$STDERR_FILE" &

RUNTIME_PID=$!

# ================================================================
# Allow startup + trace creation
# ================================================================

sleep 2

# ================================================================
# Discover trace path
# ================================================================

TRACE_FILE=$(
  grep -oE '/workspace/runs/[^ ]+/trace.jsonl' \
    "$STDERR_FILE" \
    | tail -1
)

# ================================================================
# Kill runtime abruptly
# ================================================================

kill -9 "$RUNTIME_PID" >/dev/null 2>&1 || true

sleep 1

# ================================================================
# 1️⃣ Trace file exists after crash
# ================================================================

if test -n "${TRACE_FILE:-}" &&
   test -f "$TRACE_FILE"; then

  pass "Trace survives crash"

else

  fail "Trace survives crash"

fi

# ================================================================
# 2️⃣ Trace non-empty after crash
# ================================================================

if test -s "$TRACE_FILE"; then

  pass "Partial trace persisted"

else

  fail "Partial trace persisted"

fi

# ================================================================
# 3️⃣ session_start durable
# ================================================================

if grep -q '"event": "session_start"' "$TRACE_FILE"; then

  pass "session_start durable"

else

  fail "session_start durable"

fi

# ================================================================
# 4️⃣ NDJSON integrity preserved
# ================================================================

INVALID_LINES=0

while IFS= read -r line; do

  if ! echo "$line" | jq empty >/dev/null 2>&1; then
    INVALID_LINES=$((INVALID_LINES + 1))
  fi

done < "$TRACE_FILE"

if [ "$INVALID_LINES" -eq 0 ]; then

  pass "NDJSON survives crash"

else

  fail "NDJSON survives crash"

fi

# ================================================================
# 5️⃣ No empty lines emitted
# ================================================================

EMPTY_LINES=$(
  grep -c '^$' "$TRACE_FILE" || true
)

if [ "$EMPTY_LINES" -eq 0 ]; then

  pass "No empty lines after crash"

else

  fail "No empty lines after crash"

fi

# ================================================================
# 6️⃣ Replayability after crash
# ================================================================

REPLAY_FAIL=0

while IFS= read -r line; do

  if ! echo "$line" | jq -e '
    has("timestamp") and
    (.timestamp | type == "number") and
    has("run_id") and
    (.run_id | type == "string") and
    has("event") and
    (.event | type == "string")
  ' >/dev/null 2>&1; then

    REPLAY_FAIL=$((REPLAY_FAIL + 1))

  fi

done < "$TRACE_FILE"

if [ "$REPLAY_FAIL" -eq 0 ]; then

  pass "Replayable after crash"

else

  fail "Replayable after crash"

fi

# ================================================================
# 7️⃣ Single run identity maintained
# ================================================================

RUN_ID_COUNT=$(
  cat "$TRACE_FILE" \
    | jq -r '.run_id' \
    | sort -u \
    | wc -l \
    | tr -d ' '
)

if [ "$RUN_ID_COUNT" -eq 1 ]; then

  pass "Run identity preserved"

else

  fail "Run identity preserved"

fi

# ================================================================
# 8️⃣ No truncated JSON fragments
# ================================================================

BROKEN_LINES=0

while IFS= read -r line; do

  FIRST_CHAR=$(echo "$line" | cut -c1)
  LAST_CHAR=$(echo "$line" | rev | cut -c1)

  if [ "$FIRST_CHAR" != "{" ] ||
     [ "$LAST_CHAR" != "}" ]; then

    BROKEN_LINES=$((BROKEN_LINES + 1))

  fi

done < "$TRACE_FILE"

if [ "$BROKEN_LINES" -eq 0 ]; then

  pass "No truncated writes"

else

  fail "No truncated writes"

fi

# ================================================================
# Summary
# ================================================================

echo ""
echo "============================"
echo "✅ Passed: $PASS_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -ne 0 ]; then

  echo "❌ Crash recovery validation FAILED"
  exit 1

fi

echo "🎉 Crash recovery validation passed"