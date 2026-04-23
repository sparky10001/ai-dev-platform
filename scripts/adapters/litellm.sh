#!/bin/bash
###################################################################
# litellm.sh — LiteLLM Router Adapter (v1.0 production)
#
# Single adapter that delegates all routing to LiteLLM.
# Replaces: openai.sh, ollama.sh, http-agent.sh
# Keeps:    goose.sh (agent layer), mock.sh (offline/testing)
#
# Model selected by ACTIVE_MODEL env var:
#   fast    → tinyllama (local)
#   general → tinyllama (local)
#   code    → gpt-4.1 (cloud) → tinyllama fallback
#   tooling → gpt-4.1 (cloud) → tinyllama fallback
#   claude  → claude-sonnet (cloud) → tinyllama fallback
#   smart   → best available
###################################################################

set -euo pipefail

ADAPTER_NAME="litellm"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../../.env"
TOOL_EXECUTOR="${SCRIPT_DIR}/../tool_executor.py"

source "${SCRIPT_DIR}/_base.sh"

COMMAND="${1:-}"
INPUT="${2:-}"

# ---- Load env ----
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ---- Config ----
BASE_URL="${LITELLM_BASE_URL:-http://litellm:4000/v1}"
MODEL="${ACTIVE_MODEL:-fast}"
MASTER_KEY="${LITELLM_MASTER_KEY:-ai-dev-platform}"
TIMEOUT="${AI_TIMEOUT:-60}"
RETRIES="${AI_RETRIES:-2}"

# ================================================================
# 🧠 VALIDATE
# ================================================================

if [ -z "$COMMAND" ]; then
  build_response "error" "Missing command" "invalid_request"
  adapter_exit
fi

# ================================================================
# 🧠 TOOL RESULT HANDLING
# ================================================================

if echo "$INPUT" | jq -e '.type == "tool_result"' >/dev/null 2>&1; then

  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool // "unknown"')
  TOOL_RESULT=$(echo "$INPUT" | jq -r '.result // ""')

  PROMPT="A tool was used.

Tool: ${TOOL_NAME}
Result:
${TOOL_RESULT}

Decide the next step:
- If the task is complete, provide the final answer
- If more data is needed, call another tool"

else

  # ---- Context injection ----
  CONTEXT=""
  [ -n "${ACTIVE_PROJECT:-}" ] && CONTEXT="[Project: $ACTIVE_PROJECT] "

  # ---- Tool discovery ----
  TOOL_BLOCK=""

  if command -v python3 >/dev/null 2>&1 && [ -f "$TOOL_EXECUTOR" ]; then
    RAW_TOOLS=$(python3 "$TOOL_EXECUTOR" --list-tools 2>/dev/null \
      || echo '{"tools":{}}')

    if echo "$RAW_TOOLS" | jq -e '.tools' >/dev/null 2>&1; then
      TOOL_BLOCK=$(echo "$RAW_TOOLS" | jq -r '
        if (.tools | length) == 0 then ""
        else
          "Available tools:\n" +
          (
            .tools
            | to_entries
            | map("- " + .value.name + ": " + (.value.description // ""))
            | join("\n")
          )
        end
      ')
    fi
  fi

  # ---- Build prompt ----
  case "$COMMAND" in
    run)      USER_PROMPT="${INPUT}" ;;
    fix)      USER_PROMPT="Fix this: ${INPUT}" ;;
    explain)  USER_PROMPT="Explain clearly: ${INPUT}" ;;
    refactor) USER_PROMPT="Refactor this: ${INPUT}" ;;
    query)    USER_PROMPT="${INPUT}" ;;
    *)
      build_response "error" "Unknown command: $COMMAND" "invalid_request"
      adapter_exit
      ;;
  esac

  SYSTEM="You are an AI assistant with access to tools."

  PROMPT="${SYSTEM}

${CONTEXT}${TOOL_BLOCK}

User request:
${USER_PROMPT}"

fi

# ================================================================
# 📦 REQUEST
# ================================================================

build_payload() {
  jq -n \
    --arg model "$MODEL" \
    --arg prompt "$PROMPT" \
    '{
      model: $model,
      messages: [{role: "user", content: $prompt}]
    }'
}

request_once() {
  curl -sS --max-time "$TIMEOUT" \
    -X POST "${BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -d "$(build_payload)"
}

# ================================================================
# 🔁 RETRY LOOP
# ================================================================

attempt=1
RESPONSE=""

while [ "$attempt" -le "$RETRIES" ]; do

  RESPONSE="$(request_once)"

  if [ -n "$RESPONSE" ] && json_valid "$RESPONSE"; then
    break
  fi

  RESPONSE=""
  sleep "$attempt"
  attempt=$((attempt + 1))

done

# ================================================================
# ❌ FAILURE GUARDS
# ================================================================

if [ -z "$RESPONSE" ]; then
  build_response "error" "No response from LiteLLM (${BASE_URL})" "api_error"
  adapter_exit
fi

if ! json_valid "$RESPONSE"; then
  build_response "error" "Invalid JSON from LiteLLM" "invalid_json"
  adapter_exit
fi

# ---- API error from LiteLLM ----
if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  ERR_MSG=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown error"')
  ERR_TYPE_RAW=$(echo "$RESPONSE" | jq -r '.error.type // "api_error"')
  ERR_TYPE=$(classify_error "$ERR_TYPE_RAW" "$ERR_MSG")
  build_response "error" "$ERR_MSG" "$ERR_TYPE"
  adapter_exit
fi

# ================================================================
# ✅ EXTRACT OUTPUT
# ================================================================

OUTPUT=$(echo "$RESPONSE" | jq -r '
  .choices[0].message.content //
  .response //
  .output //
  empty
')

if [ -z "$OUTPUT" ]; then
  build_response "error" "Empty response from LiteLLM" "empty_response"
  adapter_exit
fi

# ================================================================
# 🔥 TOOL CALL DETECTION
# ================================================================

TOOL_CALL_JSON=$(extract_tool_call "$OUTPUT" || true)

if [ -n "$TOOL_CALL_JSON" ]; then
  TOOL_NAME=$(echo "$TOOL_CALL_JSON" | jq -r '.name')
  TOOL_INPUT=$(echo "$TOOL_CALL_JSON" | jq -c '.input // {}')
  build_tool_call "$TOOL_NAME" "$TOOL_INPUT" "LiteLLM requested tool"
  adapter_exit
fi

# ================================================================
# ✅ SUCCESS
# ================================================================

build_response "done" "$OUTPUT" "" \
  "$(jq -n \
    --arg model "$MODEL" \
    --arg url "$BASE_URL" \
    '{provider:"litellm", model:$model, base_url:$url}')"

adapter_exit
