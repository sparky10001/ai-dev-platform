#!/bin/bash

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

read_file() {
    local path="$1"
    cat "$path"
}

write_file() {
    local path="$1"
    local content="$2"
    echo "$content" > "$path"
    echo "written:$path"
}

run_shell() {
    local cmd="$1"
    bash -c "$cmd"
}