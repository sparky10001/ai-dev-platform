#!/usr/bin/env bash
###################################################################
# run_scenario.sh — Scenario execution + evaluation loop (v3.0)
#
# Guarantees:
# - Deterministic model selection (scenario-first)
# - CLI override support (--model=...)
# - Strict JSON handling (no silent failures)
# - Trace-driven evaluation
# - Clean result persistence
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
TRACE_FLAG="--trace"

for arg in "$@"; do
  case "$arg" in
    --model=*) CLI_MODEL="${arg#*=}" ;;
    --trace) TRACE_FLAG="--trace" ;;
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

SCENARIO_DATA=$(echo "$SCENARIO_JSON" | jq -c '.data')

TASK=$(echo "$SCENARIO_DATA" | jq -r '.task')
CRITERIA=$(echo "$SCENARIO_DATA" | jq -c '.success_criteria')
SCENARIO_ID=$(echo "$SCENARIO_DATA" | jq -r '.scenario_id')
SCENARIO_MODEL=$(echo "$SCENARIO_DATA" | jq -r '.model // empty')

# ---------------------------------------------------------------
# 🎯 Resolve model (deterministic priority)
# ---------------------------------------------------------------
# Priority:
# 1. CLI override
# 2. Scenario model
# 3. Runtime default (mapping)

RESOLVED_MODEL=""

if [ -n "$CLI_MODEL" ]; then
  RESOLVED_MODEL="$CLI_MODEL"
elif [ -n "$SCENARIO_MODEL" ] && [ "$SCENARIO_MODEL" != "null" ]; then
  RESOLVED_MODEL="$SCENARIO_MODEL"
fi

MODEL_FLAG=""
if [ -n "$RESOLVED_MODEL" ]; then
  MODEL_FLAG="--model=$RESOLVED_MODEL"
fi

echo "🚀 Running agent..."
echo "Task:   $TASK"
echo "Model:  ${RESOLVED_MODEL:-runtime-default}"

# ---------------------------------------------------------------
# 🧠 Execute runtime
# ---------------------------------------------------------------

OUTPUT=$(AI_TRACE=1 bash "$RUNTIME" run "$TASK" $TRACE_FLAG $MODEL_FLAG || true)

echo "🧠 Agent output:"
echo "$OUTPUT"

# ---------------------------------------------------------------
# 📊 Read trace
# ---------------------------------------------------------------

echo "📊 Reading trace..."

TRACE_JSON=$(python3 "$EXECUTOR" read_trace '{"last_n": 200}')

TRACE_STATUS=$(echo "$TRACE_JSON" | jq -r '.status')

if [ "$TRACE_STATUS" != "success" ]; then
  echo "❌ Failed to read trace"
  echo "$TRACE_JSON" | jq
  exit 1
fi

EVENTS=$(echo "$TRACE_JSON" | jq -c '.data')

if [ "$EVENTS" = "null" ] || [ "$EVENTS" = "[]" ]; then
  echo "❌ No trace events found"
  exit 1
fi

# ---------------------------------------------------------------
# 🧪 Evaluate
# ---------------------------------------------------------------

echo "🧪 Evaluating..."

EVAL_JSON=$(python3 "$EXECUTOR" evaluate_trace "$(jq -n \
  --argjson events "$EVENTS" \
  --argjson criteria "$CRITERIA" \
  '{events: $events, criteria: $criteria}')")

echo "$EVAL_JSON" | jq

EVAL_STATUS=$(echo "$EVAL_JSON" | jq -r '.status')

if [ "$EVAL_STATUS" != "success" ]; then
  echo "❌ Evaluation failed"
  exit 1
fi

SCORE=$(echo "$EVAL_JSON" | jq -r '.data.score')

echo "--------------------------------"
echo "🎯 SCORE: $SCORE"

# ---------------------------------------------------------------
# ✅ Pass/Fail
# ---------------------------------------------------------------

PASS=$(python3 - <<EOF
score = float("$SCORE")
print("1" if score >= 1.0 else "0")
EOF
)

if [ "$PASS" != "1" ]; then
  echo "⚠️ Scenario failed"
  exit 1
fi

echo "✅ Scenario passed"

# ---------------------------------------------------------------
# 📁 Save result
# ---------------------------------------------------------------

RESULTS_DIR="${ROOT_DIR}/evals/results"
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

echo "📁 Saved result → $RESULT_FILE"