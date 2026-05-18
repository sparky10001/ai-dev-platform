#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TEST_FILE="tmp/control_plane_cli_${$}.txt"
trap 'rm -f "$TEST_FILE" tmp/file_write_flow_hello.txt tmp/hello.txt hello.txt' EXIT
rm -f "$TEST_FILE" tmp/file_write_flow_hello.txt tmp/hello.txt hello.txt

echo "[control-plane-cli] Running CLI unit tests"
python3 -m unittest control-plane/tests/test_cli.py

echo "[control-plane-cli] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

repo = Path('/workspace')
sys.path.insert(0, str(repo / 'control-plane'))
sys.path.insert(0, str(repo))
from cli.main import main
print('[control-plane-cli] Import check passed')
PY

echo "[control-plane-cli] Running command smoke checks"
./ai-orchestrate plan "list files" | jq . >/dev/null
./ai-orchestrate run "list files" | jq . >/dev/null
./ai-orchestrate run "Create a file called ${TEST_FILE} with content 'hi' and then list files" --trace | jq . >/dev/null
./ai-orchestrate validate-dag control-plane/dags/examples/file_write_flow.json | jq . >/dev/null
./ai-orchestrate execute-dag control-plane/dags/examples/file_write_flow.json | jq . >/dev/null

echo "[control-plane-cli] PASS"
