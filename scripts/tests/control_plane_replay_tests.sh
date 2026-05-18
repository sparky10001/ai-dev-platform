#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

rm -f tmp/control_plane_replay_*.txt tmp/hello.txt hello.txt

echo "[control-plane-replay] Running replay unit tests"
python3 -m unittest control-plane/tests/test_orchestration_replay.py

echo "[control-plane-replay] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.replay.loader import load_orchestration_trace
from core.replay.introspection import summarize_replay
from core.replay.exporter import export_replay_markdown
from core.replay.exporter import export_replay_summary_json
print('[control-plane-replay] Import check passed')
PY

echo "[control-plane-replay] Running replay/summarize/export smoke"
python3 - <<'PY'
import json
import os
import subprocess
from pathlib import Path

rel_path = f"tmp/control_plane_replay_{os.getpid()}.txt"
Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)
try:
    run = subprocess.run([
        '/workspace/ai-orchestrate',
        'run',
        f"Create a file called {rel_path} with content 'hi' and then list files",
        '--trace',
    ], capture_output=True, text=True, check=True)
    payload = json.loads(run.stdout)
    run_path = Path(payload['run_path'])

    subprocess.run(['/workspace/ai-orchestrate', 'replay', str(run_path)], check=True, capture_output=True, text=True)
    subprocess.run(['/workspace/ai-orchestrate', 'summarize-run', str(run_path)], check=True, capture_output=True, text=True)

    out_dir = Path('/workspace/tmp/control-plane-replay-cli')
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(['/workspace/ai-orchestrate', 'export-run', str(run_path), str(out_dir / 'summary.md')], check=True, capture_output=True, text=True)
    subprocess.run(['/workspace/ai-orchestrate', 'export-run', str(run_path), str(out_dir / 'summary.json')], check=True, capture_output=True, text=True)
finally:
    Path('/workspace').joinpath(rel_path).unlink(missing_ok=True)
print('[control-plane-replay] Smoke checks passed')
PY

echo "[control-plane-replay] PASS"
