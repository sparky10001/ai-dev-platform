#!/usr/bin/env bash
###################################################################
# run_scenario.sh — Scenario execution + evaluation loop (v6.0)
#
# Improvements:
# - Single runtime execution (fixed duplicate bug)
# - Uses read_trace as source of truth (no re-flattening)
# - Cleaner control flow
###################################################################

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXECUTOR="${ROOT_DIR}/scripts/tool_executor.py"
RUNTIME="${ROOT_DIR}/scripts/runtime.sh"

SCENARIO_PATH="${1:-}"
shift || true

if [ -z "$SCENARIO_PATH" ]; then
  echo "Usage: run_scenario.sh <scenario.json> [--model=<tier>] [--trace]"
  exit 1
fi

# ---------------------------------------------------------------
# 🔧 Parse CLI flags
# ---------------------------------------------------------------
CLI_MODEL=""
TRACE_FLAG=""

for arg in "$@"; do
  case "$arg" in
    --model=*) CLI_MODEL="${arg#*=}" ;;
    --trace)   TRACE_FLAG="--trace" ;;
  esac
done

# ---------------------------------------------------------------
# 📘 Load scenario
# ---------------------------------------------------------------
echo "📘 Loading scenario..."

SCENARIO_JSON=$(python3 "$EXECUTOR" run_scenario "{\"path\": \"$SCENARIO_PATH\"}")
STATUS=$(echo "$SCENARIO_JSON" | jq -r '.status')

if [ "$STATUS" != "success" ]; then
  echo "❌ Scenario load failed"
  echo "$SCENARIO_JSON" | jq
  exit 1
fi

SCENARIO_DATA=$(echo "$SCENARIO_JSON" | jq -c '
  if (.data | type) == "string"
  then (.data | fromjson)
  else (.data // .)
  end
')

TASK=$(echo "$SCENARIO_DATA" | jq -r '.task // empty')

if [ -z "$TASK" ]; then
  echo "❌ Scenario missing task"
  exit 1
fi

# ---------------------------------------------------------------
# 🎯 Criteria
# ---------------------------------------------------------------
CRITERIA=$(echo "$SCENARIO_DATA" | jq -c '
  .success_criteria // .criteria //
  .scenario.success_criteria // .scenario.criteria // []
')

[ -z "$CRITERIA" ] || [ "$CRITERIA" = "null" ] && CRITERIA="[]"

if [ "$(echo "$CRITERIA" | jq 'length')" -eq 0 ]; then
  echo "❌ Scenario missing success_criteria"
  exit 1
fi

SCENARIO_ID=$(echo "$SCENARIO_DATA" | jq -r '.scenario_id // "unknown_scenario"')
SCENARIO_MODEL=$(echo "$SCENARIO_DATA" | jq -r '.model // empty')

# ---------------------------------------------------------------
# 🎯 Resolve model
# ---------------------------------------------------------------
RESOLVED_MODEL=""

if [ -n "$CLI_MODEL" ]; then
  RESOLVED_MODEL="$CLI_MODEL"
elif [ -n "$SCENARIO_MODEL" ] && [ "$SCENARIO_MODEL" != "null" ]; then
  RESOLVED_MODEL="$SCENARIO_MODEL"
fi

MODEL_FLAG=""
[ -n "$RESOLVED_MODEL" ] && MODEL_FLAG="--model=$RESOLVED_MODEL"

echo "🚀 Running agent..."
echo "Task:   $TASK"
echo "Model:  ${RESOLVED_MODEL:-runtime-default}"

# ---------------------------------------------------------------
# 🧠 Execute runtime (ONCE)
# ---------------------------------------------------------------
TMP_STDERR=$(mktemp)

OUTPUT=$(AI_TRACE=1 bash "$RUNTIME" \
  run "$TASK" $TRACE_FLAG $MODEL_FLAG \
  2>"$TMP_STDERR" || true)

TRACE_FILE=$(grep "^📋 Trace:" "$TMP_STDERR" \
  | head -n1 \
  | sed 's/^📋 Trace: //' \
  | tr -d '[:space:]')

rm -f "$TMP_STDERR"

echo "🧠 Agent output:"
echo "$OUTPUT"

if [ -z "$TRACE_FILE" ] || [ ! -f "$TRACE_FILE" ]; then
  echo "❌ Trace file not found"
  exit 1
fi

echo "📋 Trace: $TRACE_FILE"

# ---------------------------------------------------------------
# 📊 Read trace (single source of truth)
# ---------------------------------------------------------------
echo "📊 Reading trace..."

TRACE_PATH_JSON=$(python3 -c "import json; print(json.dumps('$TRACE_FILE'))")

TRACE_JSON=$(python3 "$EXECUTOR" read_trace \
  "{\"path\": ${TRACE_PATH_JSON}, \"last_n\": 500}")

TRACE_STATUS=$(echo "$TRACE_JSON" | jq -r '.status')

if [ "$TRACE_STATUS" != "success" ]; then
  echo "❌ Failed to read trace"
  echo "$TRACE_JSON" | jq
  exit 1
fi

EVENTS=$(echo "$TRACE_JSON" | jq -c '.data // []')

if [ -z "$EVENTS" ] || [ "$EVENTS" = "[]" ]; then
  echo "❌ No events found"
  exit 1
fi

# Debug
TOOLS_FOUND=$(echo "$EVENTS" | python3 -c "
import json, sys
events = json.load(sys.stdin)
tools = [e.get('data') for e in events if e.get('event') == 'tool_call']
print('Tools called: ' + ', '.join(tools) if tools else 'Tools called: none')
")
echo "🔍 $TOOLS_FOUND"

# ---------------------------------------------------------------
# 🧪 Evaluate
# ---------------------------------------------------------------
echo "🧪 Evaluating..."

EVAL_INPUT=$(jq -n \
  --argjson events "$EVENTS" \
  --argjson criteria "$CRITERIA" \
  '{events: $events, criteria: $criteria}')

EVAL_JSON=$(python3 "$EXECUTOR" evaluate_trace "$EVAL_INPUT")

echo "$EVAL_JSON" | jq

SCORE=$(echo "$EVAL_JSON" | jq -r '.data.score')

echo "--------------------------------"
echo "🎯 SCORE: $SCORE"

PASS=$(python3 -c "print('1' if float('$SCORE') >= 1.0 else '0')")

if [ "$PASS" != "1" ]; then
  echo "⚠️ Scenario failed"
  exit 1
fi

echo "✅ Scenario passed"

# ---------------------------------------------------------------
# 📁 Save result
# ---------------------------------------------------------------
RESULTS_DIR="${ROOT_DIR}/logs/evals"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
RESULT_FILE="${RESULTS_DIR}/${SCENARIO_ID}_${TIMESTAMP}.json"

jq -n \
  --arg scenario "$SCENARIO_ID" \
  --arg timestamp "$TIMESTAMP" \
  --arg model "${RESOLVED_MODEL:-${ACTIVE_MODEL:-runtime-default}}" \
  --argjson eval "$EVAL_JSON" \
  '{
    scenario_id: $scenario,
    timestamp: $timestamp,
    model: $model,
    score: $eval.data.score,
    passed: $eval.data.passed,
    total: $eval.data.total,
    results: $eval.data.results
  }' > "$RESULT_FILE"

# ---------------------------------------------------------------
# 🧹 Log maintenance
# ---------------------------------------------------------------
python3 "$ROOT_DIR/scripts/maintenance/log_manager.py" \
  --protect "$TRACE_FILE" || true

echo "📁 Saved → $RESULT_FILE"