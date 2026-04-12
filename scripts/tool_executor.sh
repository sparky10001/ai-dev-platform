#!/bin/bash
###################################################################
# tool_executor.sh — Production-safe tool execution layer
#
# Responsibilities:
#   - Validate tool calls
#   - Enforce safety constraints
#   - Execute tools from registry
#   - Return structured JSON contract
###################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_FILE="${SCRIPT_DIR}/../tools/registry.sh"

# ---- Config ----
TOOL_TIMEOUT="${TOOL_TIMEOUT:-10}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(pwd)}"
MAX_OUTPUT_SIZE="${MAX_OUTPUT_SIZE:-5000}"

# ---- Load tools ----
if [ ! -f "$TOOLS_FILE" ]; then
    echo "❌ Tool registry not found: $TOOLS_FILE"
    exit 1
fi

source "$TOOLS_FILE"

# ---- Args ----
TOOL_NAME="${1:-}"
TOOL_INPUT_JSON="${2:-{}}"

if [ -z "$TOOL_NAME" ]; then
    echo "❌ No tool name provided"
    exit 1
fi

# ---- Helpers ----

json_response() {
    local status="$1"
    local output="$2"

    jq -n \
        --arg status "$status" \
        --arg output "$output" \
        --arg tool "$TOOL_NAME" \
        '{
          status: $status,
          output: $output,
          meta: {
            tool: $tool
          }
        }'
}

safe_path() {
    local path="$1"

    # Resolve absolute path
    local resolved
    resolved=$(realpath -m "$path" 2>/dev/null || echo "")

    # Ensure inside workspace
    if [[ "$resolved" != "$WORKSPACE_ROOT"* ]]; then
        echo ""
        return 1
    fi

    echo "$resolved"
}

truncate_output() {
    local data="$1"
    echo "$data" | head -c "$MAX_OUTPUT_SIZE"
}

# ---- Parse input ----
get_field() {
    local field="$1"
    echo "$TOOL_INPUT_JSON" | jq -r "$field // empty" 2>/dev/null || echo ""
}

# ---- Tool dispatcher ----
execute() {

    case "$TOOL_NAME" in

        # =============================
        # 📄 read_file
        # =============================
        read_file)
            local path
            path=$(get_field '.path')

            if [ -z "$path" ]; then
                json_response "error" "Missing 'path'"
                return
            fi

            safe=$(safe_path "$path") || {
                json_response "error" "Invalid path (outside workspace)"
                return
            }

            if [ ! -f "$safe" ]; then
                json_response "error" "File not found: $path"
                return
            fi

            content=$(cat "$safe")
            content=$(truncate_output "$content")

            json_response "success" "$content"
            ;;

        # =============================
        # ✏️ write_file
        # =============================
        write_file)
            local path content
            path=$(get_field '.path')
            content=$(get_field '.content')

            if [ -z "$path" ]; then
                json_response "error" "Missing 'path'"
                return
            fi

            safe=$(safe_path "$path") || {
                json_response "error" "Invalid path (outside workspace)"
                return
            }

            mkdir -p "$(dirname "$safe")"
            echo "$content" > "$safe"

            json_response "success" "written:$path"
            ;;

        # =============================
        # 🖥 run_shell (SAFE MODE)
        # =============================
        run_shell)
            local cmd
            cmd=$(get_field '.cmd')

            if [ -z "$cmd" ]; then
                json_response "error" "Missing 'cmd'"
                return
            fi

            # ---- Allowlist (STRICT) ----
            ALLOWED_PREFIXES=(
                "ls"
                "cat"
                "echo"
                "pwd"
                "head"
                "tail"
                "wc"
            )

            allowed=false
            for prefix in "${ALLOWED_PREFIXES[@]}"; do
                if [[ "$cmd" == "$prefix"* ]]; then
                    allowed=true
                    break
                fi
            done

            if [ "$allowed" = false ]; then
                json_response "error" "Command not allowed"
                return
            fi

            result=$(timeout "$TOOL_TIMEOUT" bash -c "$cmd" 2>&1 || true)
            result=$(truncate_output "$result")

            json_response "success" "$result"
            ;;

        # =============================
        # ❌ Unknown tool
        # =============================
        *)
            json_response "error" "Unknown tool: $TOOL_NAME"
            ;;
    esac
}

# ---- Execute safely ----
if ! OUTPUT=$(execute 2>&1); then
    json_response "error" "Execution failure"
    exit 1
fi

echo "$OUTPUT"