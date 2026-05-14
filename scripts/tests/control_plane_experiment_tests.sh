#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-experiments] Running experiment unit tests"
python3 -m unittest control-plane/tests/test_orchestration_experiments.py

echo "[control-plane-experiments] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.experiments.tracker import track_replay
from core.experiments.datasets import build_replay_dataset
print('[control-plane-experiments] Import check passed')
PY

echo "[control-plane-experiments] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

run1 = subprocess.run(['/workspace/ai-orchestrate', 'run', 'list files', '--trace'], capture_output=True, text=True, check=True)
run2 = subprocess.run(['/workspace/ai-orchestrate', 'run', "Create a file called hello.txt with content 'hi' and then list files", '--trace'], capture_output=True, text=True, check=True)
r1 = json.loads(run1.stdout)['run_path']
r2 = json.loads(run2.stdout)['run_path']

subprocess.run(['/workspace/ai-orchestrate', 'track-run', r1], check=True, capture_output=True, text=True)
subprocess.run(['/workspace/ai-orchestrate', 'track-experiment', r1, r2], check=True, capture_output=True, text=True)
subprocess.run(['/workspace/ai-orchestrate', 'build-dataset', r1, r2], check=True, capture_output=True, text=True)

out = Path('/workspace/tmp/control-plane-experiment-export')
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-experiment', r1, r2, str(out / 'manifest.md')], check=True, capture_output=True, text=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-experiment', r1, r2, str(out / 'manifest.json')], check=True, capture_output=True, text=True)
print('[control-plane-experiments] Smoke flow passed')
PY

echo "[control-plane-experiments] PASS"
