#!/usr/bin/env bash
###################################################################
# run_scenario.sh — Scenario execution + evaluation loop (v5.0)
#
# Fixes from v4.0:
# - CRITICAL: now captures per-session trace path from runtime stderr
#   (was reading .ai_trace.log — the old shared file — instead of
#   the per-session .ai_trace.{SESSION_ID}.log that runtime writes)
# - Passes exact trace path to read_trace tool
# - Flattens nested meta.trace events from agent_output event
#   so evaluate_trace sees tool_call events directly
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

# Normalize (handles stringified JSON)
SCENARIO_DATA=$(echo "$SCENARIO_JSON" | jq -c '
  if (.data | type) == "string"
  then (.data | fromjson)
  else (.data // .)
  end
')

if [ -z "$SCENARIO_DATA" ] || [ "$SCENARIO_DATA" = "null" ]; then
  echo "❌ Scenario data empty after normalization"
  exit 1
fi

TASK=$(echo "$SCENARIO_DATA" | jq -r '.task // empty')

if [ -z "$TASK" ]; then
  echo "❌ Scenario missing task"
  echo "$SCENARIO_DATA" | jq
  exit 1
fi

# ---------------------------------------------------------------
# 🎯 Extract criteria
# ---------------------------------------------------------------

CRITERIA=$(echo "$SCENARIO_DATA" | jq -c '
  .success_criteria // .criteria //
  .scenario.success_criteria // .scenario.criteria // []
')

[ -z "$CRITERIA" ] || [ "$CRITERIA" = "null" ] && CRITERIA="[]"

CRITERIA_LEN=$(echo "$CRITERIA" | jq 'length')

if [ "$CRITERIA_LEN" -eq 0 ]; then
  echo "❌ Scenario missing success_criteria"
  echo "$SCENARIO_DATA" | jq
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
# 🧠 Execute runtime
#
# Fix v5.0: Capture stderr separately so we can extract the
# per-session trace path that runtime.sh prints to stderr.
# runtime.sh prints: "📋 Trace: /path/to/.ai_trace.SESSION.log"
# ---------------------------------------------------------------

TMP_STDERR=$(mktemp)

OUTPUT=$(AI_TRACE=1 bash "$RUNTIME" \
  run "$TASK" $TRACE_FLAG $MODEL_FLAG \
  2>"$TMP_STDERR" || true)

# Extract trace path from runtime stderr
TRACE_FILE=$(grep "^📋 Trace:" "$TMP_STDERR" \
  | head -n1 \
  | sed 's/^📋 Trace: //' \
  | tr -d '[:space:]')

rm -f "$TMP_STDERR"

echo "🧠 Agent output:"
echo "$OUTPUT"

if [ -z "$TRACE_FILE" ] || [ ! -f "$TRACE_FILE" ]; then
  echo "❌ Trace file not found: '${TRACE_FILE}'"
  echo "   Ensure runtime.sh has TRACE_ENABLED=1 and --trace flag"
  exit 1
fi

echo "📋 Trace: $TRACE_FILE"

# ---------------------------------------------------------------
# 📊 Read trace from the exact session file
#
# Fix v5.0: Pass explicit path to read_trace — was reading
# default .ai_trace.log (old shared file) instead of the
# per-session file runtime.sh creates
# ---------------------------------------------------------------

echo "📊 Reading trace..."

# Escape path for JSON
TRACE_PATH_JSON=$(python3 -c "import json; print(json.dumps('$TRACE_FILE'))")

RAW_TRACE_OUTPUT=$(python3 "$EXECUTOR" read_trace \
  "{\"path\": ${TRACE_PATH_JSON}, \"last_n\": 500}" 2>&1)

TRACE_JSON=$(echo "$RAW_TRACE_OUTPUT" | sed -n '/^{/,$p')

if ! echo "$TRACE_JSON" | jq empty >/dev/null 2>&1; then
  echo "❌ Invalid JSON from read_trace"
  echo "$RAW_TRACE_OUTPUT"
  exit 1
fi

TRACE_STATUS=$(echo "$TRACE_JSON" | jq -r '.status // empty')

if [ "$TRACE_STATUS" != "success" ]; then
  echo "❌ Failed to read trace"
  echo "$TRACE_JSON" | jq
  exit 1
fi

# ---------------------------------------------------------------
# 📦 Extract + flatten events
#
# The trace file contains:
#   - runtime events (start, agent_output, end)
#   - agent_output.data.meta.trace contains nested tool_call events
#
# We need to flatten so evaluate_trace sees tool_call events directly.
# ---------------------------------------------------------------

RAW_EVENTS=$(echo "$TRACE_JSON" | jq -c '.data // []')

# Flatten: extract nested tool_call events from agent_output.data.meta.trace
EVENTS=$(python3 - <<PYEOF
import json, sys

raw = json.loads("""${RAW_EVENTS}""")

def flatten(events):
    out = []
    for e in events:
        if not isinstance(e, dict):
            continue
        out.append(e)
        # Dig into agent_output nested trace
        data = e.get("data", {})
        if isinstance(data, dict):
            meta = data.get("meta", {})
            if isinstance(meta, dict):
                for sub in meta.get("trace", []):
                    out.append(sub)
        # Dig into direct meta.trace
        meta = e.get("meta", {})
        if isinstance(meta, dict):
            for sub in meta.get("trace", []):
                out.append(sub)
    return out

flattened = flatten(raw)
print(json.dumps(flattened))
PYEOF
)

if [ -z "$EVENTS" ] || [ "$EVENTS" = "null" ] || [ "$EVENTS" = "[]" ]; then
  echo "❌ No events found in trace"
  exit 1
fi

# Quick debug — show tool calls found
TOOLS_FOUND=$(echo "$EVENTS" | python3 -c "
import json, sys
events = json.load(sys.stdin)
tools = [e.get('data') for e in events if e.get('event') == 'tool_call']
print('Tools called: ' + ', '.join(tools) if tools else 'Tools called: none')
")
echo "🔍 $TOOLS_FOUND"

# ---------------------------------------------------------------
# 🧪 Build evaluation input
# ---------------------------------------------------------------

EVAL_INPUT=$(jq -n \
  --argjson events "$EVENTS" \
  --argjson criteria "$CRITERIA" \
  '{events: $events, criteria: $criteria}')

# ---------------------------------------------------------------
# 🧪 Evaluate
# ---------------------------------------------------------------

echo "🧪 Evaluating..."

EVAL_JSON=$(python3 "$EXECUTOR" evaluate_trace "$EVAL_INPUT")

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

PASS=$(python3 -c "
score = float('$SCORE')
print('1' if score >= 1.0 else '0')
")

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

echo "📁 Saved → $RESULT_FILE"
