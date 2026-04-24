#!/bin/bash
###################################################################
# runtime.sh — Stable AI Runtime (v5.7 FINAL)
#
# Features:
#   - Strict contract enforcement (JSON required)
#   - Exit-code safe adapter handling
#   - Structured tool execution loop
#   - Modular error handling
#   - Step-safe structured trace logging
#   - Hardened tool executor handling
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
ADAPTERS_DIR="${SCRIPT_DIR}/adapters"
TOOL_EXECUTOR="${SCRIPT_DIR}/tool_executor.sh"
TRACE_LOG="${SCRIPT_DIR}/../.ai_trace.log"

# ---- Load environment ----
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# ---- Args ----
COMMAND=${1:-}
shift || true

if [ -z "$COMMAND" ]; then
    echo "Usage: ai [run|explain|refactor|fix|query] <args>"
    exit 1
fi

# ---- Defaults ----
TRACE=0
MAX_STEPS=1
BUDGET=""
AI_TIMEOUT="${AI_TIMEOUT:-30}"

# ---- Parse flags ----
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --trace) TRACE=1 ;;
        --max-steps=*) MAX_STEPS="${1#*=}" ;;
        --budget=*) BUDGET="${1#*=}" ;;
        *) ARGS+=("$1") ;;
    esac
    shift
done

INPUT="${ARGS[*]}"

# ---- Adapter ----
ADAPTER_NAME="${AI_ADAPTER:-goose}"
ADAPTER="${ADAPTERS_DIR}/${ADAPTER_NAME}.sh"

if [ ! -f "$ADAPTER" ]; then
    echo "❌ Adapter not found: $ADAPTER_NAME"
    exit 1
fi

# ---- Trace logging ----
log_event() {
    local step="$1"
    local event="$2"
    local data="$3"

    jq -n \
      --arg step "$step" \
      --arg event "$event" \
      --arg data "$data" \
      '{
        step: ($step | tonumber),
        event: $event,
        data: $data,
        timestamp: now
      }' >> "$TRACE_LOG" 2>/dev/null || true
}

# ---- Tool executor validation (NOW SAFE) ----
if [ ! -f "$TOOL_EXECUTOR" ]; then
    echo "❌ Tool executor not found: $TOOL_EXECUTOR"
    log_event "0" "tool_error" "executor_missing"
    exit 1
fi

if [ ! -x "$TOOL_EXECUTOR" ]; then
    echo "⚠️ Tool executor not executable — fixing..."
    chmod +x "$TOOL_EXECUTOR"
fi

# ---- JSON helpers ----
json_get() {
    local expr="$1"
    echo "$PARSED_JSON" | jq -r "$expr // empty"
}

# ---- Error handler ----
handle_error() {
    local error_type="$1"
    local message="$2"

    echo "❌ Adapter error:"

    case "$error_type" in
        invalid_api_key)
            echo "🔑 Invalid or missing API key"
            echo "👉 Set OPENAI_API_KEY in .env"
            ;;
        insufficient_quota)
            echo "💳 API quota exceeded"
            echo "👉 Add credits or switch provider"
            ;;
        rate_limit_exceeded)
            echo "⏳ Rate limit hit — retry later"
            ;;
        invalid_request)
            echo "⚠️ Invalid request"
            echo "$message"
            ;;
        invalid_json)
            echo "⚠️ Adapter returned invalid JSON"
            echo "$message"
            ;;
        system_failure)
            echo "💥 Adapter crashed or timed out"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# ---- Runtime engine ----
runtime_execute() {
    local command="$1"
    local input="$2"

    local step=1
    local raw_output=""
    local status=""
    local clean_output=""
    local next_input=""
    local tool_name=""
    local tool_input=""
    local last_tool=""
    local PARSED_JSON=""

    while [ "$step" -le "$MAX_STEPS" ]; do

        if [ -n "$BUDGET" ] && [ "$step" -gt "$BUDGET" ]; then
            [ "$TRACE" -eq 1 ] && echo "⚠️ Budget limit reached"
            break
        fi

        [ "$TRACE" -eq 1 ] && echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        [ "$TRACE" -eq 1 ] && echo "🔁 Step $step / $MAX_STEPS"
        [ "$TRACE" -eq 1 ] && echo "📥 Input: $input"

        log_event "$step" "step_start" "$input"

        # ---- Execute adapter safely ----
        raw_output=""
        adapter_exit=0

        raw_output=$("$ADAPTER" "$command" "$input") || adapter_exit=$?

        if [ $adapter_exit -ne 0 ]; then
            echo "⚠️ Adapter system failure (exit $adapter_exit)"
            log_event "$step" "adapter_error" "system_failure"
            handle_error "system_failure" "Adapter crashed or timed out"
            return 1
        fi

        if [ -z "$raw_output" ]; then
            echo "⚠️ Empty adapter response"
            log_event "$step" "adapter_error" "empty_response"
            return 1
        fi

        # ---- Strict JSON validation ----
        if ! echo "$raw_output" | jq empty >/dev/null 2>&1; then
            echo "❌ Invalid JSON from adapter"
            log_event "$step" "adapter_error" "invalid_json"
            handle_error "invalid_json" "$raw_output"
            return 1
        fi

        PARSED_JSON="$raw_output"

        # ---- Extract fields ----
        status=$(json_get '.status')

        if [ -z "$status" ] || [ "$status" = "null" ]; then
            echo "❌ Invalid or missing status in adapter response"
            log_event "$step" "adapter_error" "invalid_contract"
            return 1
        fi

        clean_output=$(json_get '.output')
        next_input=$(json_get '.next_input')

        tool_name=$(json_get '.tool_call.name')
        [ "$tool_name" = "null" ] && tool_name=""

        tool_input=$(echo "$PARSED_JSON" | jq -c '
          if .tool_call.input == null then {}
          elif (.tool_call.input | type) == "object" then .tool_call.input
          elif (.tool_call.input | type) == "string" then
            try (.tool_call.input | fromjson) catch {}
          else {}
          end
        ')

        [ "$TRACE" -eq 1 ] && echo "📤 Output: $clean_output"
        [ "$TRACE" -eq 1 ] && echo "📊 Status: $status"

        log_event "$step" "adapter_output" "$clean_output"

        # ==========================================================
        # 🔥 TOOL EXECUTION
        # ==========================================================
        if [ "$status" = "tool_call" ]; then

            if [ -z "$tool_name" ]; then
                echo "❌ Invalid tool call (missing name)"
                log_event "$step" "tool_error" "missing_name"
                return 1
            fi

            if [ "$tool_name" = "$last_tool" ]; then
                echo "⚠️ Repeated tool call: $tool_name"
                log_event "$step" "tool_loop_detected" "$tool_name"
                return 1
            fi

            last_tool="$tool_name"

            [ "$TRACE" -eq 1 ] && echo "🛠️ Tool: $tool_name"
            [ "$TRACE" -eq 1 ] && echo "📦 Input: $tool_input"

            log_event "$step" "tool_call" "$tool_name"

            if ! TOOL_RESULT=$("$TOOL_EXECUTOR" "$tool_name" "$tool_input"); then
                echo "❌ Tool execution failed"
                log_event "$step" "tool_error" "execution_failed"
                return 1
            fi

            log_event "$step" "tool_result" "$TOOL_RESULT"

            # Normalize tool output
            if echo "$TOOL_RESULT" | jq empty >/dev/null 2>&1; then
                tool_output=$(echo "$TOOL_RESULT" | jq -r '.output // .')
            else
                tool_output="$TOOL_RESULT"
            fi

            # ---- Structured injection ----
            input=$(jq -n \
              --arg tool "$tool_name" \
              --arg result "$tool_output" \
              --arg command "$command" \
              '{
                type: "tool_result",
                tool: $tool,
                result: $result,
                next_task: $command
              }')

            ((step++))
            continue
        fi
        # ==========================================================

        # ---- State machine ----
        case "$status" in

            done)
                [ "$TRACE" -eq 0 ] && [ -n "$clean_output" ] && echo "$clean_output"
                return 0
                ;;

            error)
                error_type=$(echo "$PARSED_JSON" | jq -r '.meta.error_type // "unknown"')
                [ "$TRACE" -eq 1 ] && echo "❌ Error Type: $error_type"

                handle_error "$error_type" "$clean_output"
                log_event "$step" "adapter_error" "$error_type"
                return 1
                ;;

            continue|running)
                input="${next_input:-$clean_output}"
                ;;

            *)
                echo "⚠️ Unknown status: $status"
                echo "$clean_output"
                return 1
                ;;
        esac

        ((step++))
    done

    [ -n "$clean_output" ] && echo "$clean_output"
}

# ---- Execute ----
runtime_execute "$COMMAND" "$INPUT"