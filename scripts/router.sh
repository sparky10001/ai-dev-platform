#!/bin/bash
###################################################################
# router.sh — Smart Router v3.1 (Unified Normalizer)
#
# Fixes:
# - Unified response contract across all adapters
# - tool_call is OPTIONAL (never treated as failure)
# - Ollama/OpenAI/mock normalization layer
# - Hardens fallback reliability
# - Removes brittle status assumptions
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---------------------------------------------------------------
# Load env
# ---------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ---------------------------------------------------------------
# Loop protection
# ---------------------------------------------------------------
if [ "${ROUTER_ACTIVE:-false}" = "true" ]; then
  echo "❌ Router recursion detected"
  exit 1
fi

export ROUTER_ACTIVE=true

# ---------------------------------------------------------------
# Config
# ---------------------------------------------------------------
AI_ADAPTER="${AI_ADAPTER:-auto}"
MODEL_PROVIDER="${MODEL_PROVIDER:-local}"
FALLBACK_CHAIN="${FALLBACK_CHAIN:-ollama,http-agent,mock}"

IFS=',' read -ra FALLBACKS <<< "$FALLBACK_CHAIN"

LOWER_INPUT=$(echo "${INPUT:-}" | tr '[:upper:]' '[:lower:]' 2>/dev/null || echo "")

# ---------------------------------------------------------------
# Task classification (lightweight heuristic)
# ---------------------------------------------------------------
TASK_TYPE="general"

if [[ "$LOWER_INPUT" == *"file"* ]] || [[ "$LOWER_INPUT" == *"read"* ]]; then
  TASK_TYPE="tooling"
elif [[ "$LOWER_INPUT" == *"fix"* ]] || [[ "$LOWER_INPUT" == *"refactor"* ]]; then
  TASK_TYPE="code"
elif [[ "$COMMAND" == "query" ]]; then
  TASK_TYPE="fast"
fi

# ---------------------------------------------------------------
# Adapter selection
# ---------------------------------------------------------------
select_adapter() {

  if [ "$AI_ADAPTER" != "auto" ]; then
    echo "$AI_ADAPTER"
    return
  fi

  case "$TASK_TYPE" in
    tooling)
      command -v goose >/dev/null 2>&1 && echo "goose" || echo "ollama"
      ;;
    code)
      [ -n "${OPENAI_API_KEY:-}" ] && echo "openai" || echo "ollama"
      ;;
    fast)
      [ -n "${OPENAI_API_KEY:-}" ] && echo "openai" || echo "ollama"
      ;;
    *)
      case "$MODEL_PROVIDER" in
        openai) echo "openai" ;;
        local)  echo "ollama" ;;
        mock)   echo "mock" ;;
        *)      echo "http-agent" ;;
      esac
      ;;
  esac
}

PRIMARY_ADAPTER="$(select_adapter)"

# ---------------------------------------------------------------
# Adapter resolution
# ---------------------------------------------------------------
resolve_adapter() {
  case "$1" in
    openai)     echo "${SCRIPT_DIR}/adapters/openai.sh" ;;
    http-agent) echo "${SCRIPT_DIR}/adapters/http-agent.sh" ;;
    goose)      echo "${SCRIPT_DIR}/adapters/goose.sh" ;;
    ollama)     echo "${SCRIPT_DIR}/adapters/ollama.sh" ;;
    mock)       echo "${SCRIPT_DIR}/adapters/mock.sh" ;;
    *)          echo "" ;;
  esac
}

# ---------------------------------------------------------------
# Execution safety check
# ---------------------------------------------------------------
can_run_adapter() {
  case "$1" in
    openai) [ -n "${OPENAI_API_KEY:-}" ] ;;
    ollama) command -v curl >/dev/null 2>&1 ;;
    goose)  command -v goose >/dev/null 2>&1 ;;
    http-agent|mock) return 0 ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------
# NORMALIZATION CORE (🔥 KEY FIX)
# ---------------------------------------------------------------
normalize_response() {

  local raw="$1"
  local adapter="$2"

  # Extract text from any provider format
  local output
  output="$(echo "$raw" | jq -r '
    .response //
    .output //
    .message.content //
    .choices[0].message.content //
    empty
  ')"

  # Extract tool call if present (optional!)
  local tool_call
  tool_call="$(echo "$raw" | jq -c '
    .tool_call //
    .tool //
    null
  ' 2>/dev/null || echo "null")"

  # Final unified contract (ALWAYS VALID)
  jq -n \
    --arg status "done" \
    --arg output "$output" \
    --argjson tool_call "$tool_call" \
    --arg adapter "$adapter" \
    '{
      status: $status,
      output: $output,
      tool_call: $tool_call,
      meta: {
        adapter: $adapter,
        normalized: true,
        timestamp: now
      }
    }'
}

# ---------------------------------------------------------------
# Run adapter
# ---------------------------------------------------------------
run_adapter() {
  local adapter="$1"
  local path

  path="$(resolve_adapter "$adapter")"

  if [ -z "$path" ] || [ ! -f "$path" ]; then
    return 1
  fi

  if ! can_run_adapter "$adapter"; then
    return 1
  fi

  RESPONSE="$("$path" "$COMMAND" "$INPUT" 2>/dev/null || true)"

  if [ -z "$RESPONSE" ]; then
    return 1
  fi

  # IMPORTANT: DO NOT validate tool_call presence anymore
  echo "$(normalize_response "$RESPONSE" "$adapter")"
  return 0
}

# ---------------------------------------------------------------
# Execution chain
# ---------------------------------------------------------------
EXECUTION_ORDER=("$PRIMARY_ADAPTER")

for fb in "${FALLBACKS[@]}"; do
  [[ "$fb" != "$PRIMARY_ADAPTER" ]] && EXECUTION_ORDER+=("$fb")
done

if [ "${AI_DEBUG:-false}" = "true" ]; then
  echo "🧠 Task: $TASK_TYPE" >&2
  echo "🎯 Primary: $PRIMARY_ADAPTER" >&2
  echo "🔁 Chain: ${EXECUTION_ORDER[*]}" >&2
fi

# ---------------------------------------------------------------
# Execute chain
# ---------------------------------------------------------------
for adapter in "${EXECUTION_ORDER[@]}"; do

  RESPONSE="$(run_adapter "$adapter" || true)"

  if [ -n "$RESPONSE" ]; then
    echo "$RESPONSE"
    exit 0
  fi

done

# ---------------------------------------------------------------
# Final fallback (never fail empty anymore)
# ---------------------------------------------------------------
echo "$(jq -n \
  --arg msg "All adapters failed" \
  '{
    status:"error",
    output:$msg,
    tool_call:null,
    meta:{router:"v3.1"}
  }')"

exit 0