#!/usr/bin/env bash
###################################################################
# run_scenario.sh — Stable Scenario Runner (v3.2)
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUNTIME="${ROOT_DIR}/scripts/runtime.sh"
LOADER="${ROOT_DIR}/scripts/run_scenario.py"
EXECUTOR="${ROOT_DIR}/scripts/tool_executor.py"

SCENARIO_PATH="${1:-}"
shift || true

if [ -z "$SCENARIO_PATH" ]; then
  echo "Usage: run_scenario.sh <scenario.json> [--model=<tier>] [--trace]"
  exit 1
fi

# ===============================================================
# FLAGS
# ===============================================================

MODEL=""
TRACE=0

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

OUTPUT_JSON=$("${CMD[@]}")

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

EVAL_OUTPUT=$(python3 "$EXECUTOR" evaluate_trace "$EVAL_INPUT")

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