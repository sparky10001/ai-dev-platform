#!/usr/bin/env bash
###################################################################
# runtime_run_scenario.sh — Stable Scenario Runner (v3.3)
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"
LOADER="${ROOT_DIR}/scripts/runtime_run_scenario.py"
EXECUTOR="${ROOT_DIR}/scripts/tool_executor.py"

SCENARIO_PATH="${1:-}"
shift || true

if [ -z "$SCENARIO_PATH" ]; then
  echo "Usage: runtime_run_scenario.sh <scenario.json> [--model=<tier>] [--trace]"
  exit 1
fi

# ===============================================================
# FLAGS
# ===============================================================

MODEL=""
TRACE=0
SCENARIO_TIMEOUT="${SCENARIO_TIMEOUT:-60}"

for arg in "$@"; do
  case "$arg" in
    --model=*)
      MODEL="${arg#*=}"
      ;;
    --trace)
      TRACE=1
      ;;
  esac
done

if ! [[ "$SCENARIO_TIMEOUT" =~ ^[1-9][0-9]*$ ]]; then
  echo "❌ SCENARIO_TIMEOUT must be a positive integer (seconds), got: $SCENARIO_TIMEOUT"
  exit 2
fi

# ===============================================================
# LOAD SCENARIO
# ===============================================================

echo "📘 Loading scenario..."

SCENARIO_JSON=$(python3 "$LOADER" "$SCENARIO_PATH")

STATUS=$(echo "$SCENARIO_JSON" | jq -r '.status // empty')

if [ "$STATUS" != "success" ]; then
  echo "$SCENARIO_JSON" | jq .
  exit 1
fi

SCENARIO_DATA=$(echo "$SCENARIO_JSON" | jq -c '.data')

TASK=$(echo "$SCENARIO_DATA" | jq -r '.task // empty')

if [ -z "$TASK" ]; then
  echo "❌ Scenario missing task"
  exit 1
fi

CRITERIA=$(echo "$SCENARIO_DATA" | jq -c '.success_criteria // []')

echo "🚀 Running scenario..."
echo "Task:  $TASK"

# ===============================================================
# EXECUTE RUNTIME
# ===============================================================

CMD=(
  bash
  "$RUNTIME"
  run
  "$TASK"
)

if [ "$TRACE" -eq 1 ]; then
  CMD+=(--trace)
fi

if [ -n "$MODEL" ]; then
  CMD+=(--model="$MODEL")
fi

RUNTIME_STDOUT="$(mktemp)"
RUNTIME_STDERR="$(mktemp)"
EVAL_STDOUT="$(mktemp)"
EVAL_STDERR="$(mktemp)"

cleanup() {
  rm -f "$RUNTIME_STDOUT" "$RUNTIME_STDERR" "$EVAL_STDOUT" "$EVAL_STDERR"
}
trap cleanup EXIT

set +e
timeout "$SCENARIO_TIMEOUT" "${CMD[@]}" >"$RUNTIME_STDOUT" 2>"$RUNTIME_STDERR"
RUNTIME_EXIT=$?
set -e

if [ "$RUNTIME_EXIT" -eq 124 ]; then
  echo "❌ Scenario runtime timed out after ${SCENARIO_TIMEOUT}s"
  [ -s "$RUNTIME_STDERR" ] && cat "$RUNTIME_STDERR"
  exit 124
fi

if [ "$RUNTIME_EXIT" -ne 0 ]; then
  echo "❌ Scenario runtime failed (exit=$RUNTIME_EXIT)"
  [ -s "$RUNTIME_STDOUT" ] && cat "$RUNTIME_STDOUT"
  [ -s "$RUNTIME_STDERR" ] && cat "$RUNTIME_STDERR"
  exit "$RUNTIME_EXIT"
fi

OUTPUT_JSON="$(cat "$RUNTIME_STDOUT")"

# ===============================================================
# VALIDATE RUNTIME JSON
# ===============================================================

if ! echo "$OUTPUT_JSON" | jq empty >/dev/null 2>&1; then
  echo "❌ Runtime produced invalid JSON"
  echo "$OUTPUT_JSON"
  exit 1
fi

echo "🧠 Runtime output:"
echo "$OUTPUT_JSON" | jq .

# ===============================================================
# EXTRACT TRACE SAFELY
# ===============================================================

TRACE_JSON=$(echo "$OUTPUT_JSON" | jq -c '.meta.trace // []')

# normalize to guaranteed valid compact json
TRACE_JSON=$(echo "$TRACE_JSON" | jq -c '.' 2>/dev/null || echo '[]')

CRITERIA_JSON=$(echo "$CRITERIA" | jq -c '.' 2>/dev/null || echo '[]')

# ===============================================================
# BUILD EVALUATION INPUT
# ===============================================================

EVAL_INPUT=$(jq -n \
  --argjson events "$TRACE_JSON" \
  --argjson criteria "$CRITERIA_JSON" \
  '{
      events: $events,
      criteria: $criteria
    }')

# ===============================================================
# RUN EVALUATION
# ===============================================================

set +e
timeout "$SCENARIO_TIMEOUT" python3 "$EXECUTOR" evaluate_trace "$EVAL_INPUT" >"$EVAL_STDOUT" 2>"$EVAL_STDERR"
EVAL_EXIT=$?
set -e

if [ "$EVAL_EXIT" -eq 124 ]; then
  echo "❌ Scenario evaluation timed out after ${SCENARIO_TIMEOUT}s"
  [ -s "$EVAL_STDERR" ] && cat "$EVAL_STDERR"
  exit 124
fi

if [ "$EVAL_EXIT" -ne 0 ]; then
  echo "❌ Scenario evaluation failed (exit=$EVAL_EXIT)"
  [ -s "$EVAL_STDOUT" ] && cat "$EVAL_STDOUT"
  [ -s "$EVAL_STDERR" ] && cat "$EVAL_STDERR"
  exit "$EVAL_EXIT"
fi

EVAL_OUTPUT="$(cat "$EVAL_STDOUT")"

if ! echo "$EVAL_OUTPUT" | jq empty >/dev/null 2>&1; then
  echo "❌ Evaluation produced invalid JSON"
  echo "$EVAL_OUTPUT"
  exit 1
fi

echo "🧪 Evaluation:"
echo "$EVAL_OUTPUT" | jq .

SCORE=$(echo "$EVAL_OUTPUT" | jq -r '.data.score // 0')

echo "--------------------------------"
echo "🎯 SCORE: $SCORE"

PASS=$(python3 -c "print(1 if float('$SCORE') >= 1.0 else 0)")

if [ "$PASS" != "1" ]; then
  echo "⚠️ Scenario failed"
  exit 1
fi

echo "✅ Scenario passed"
