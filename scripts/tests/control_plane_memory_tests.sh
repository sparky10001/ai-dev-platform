#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[control-plane-memory] Running memory unit tests"
python3 -m unittest control-plane/tests/test_orchestration_memory.py

echo "[control-plane-memory] Running import check"
python3 - <<'PY'
import sys
from pathlib import Path

cp_root = Path('/workspace/control-plane')
if str(cp_root) not in sys.path:
    sys.path.insert(0, str(cp_root))

from core.memory.history import build_memory_timeline
from core.memory.retrieval import retrieve_memory_records
print('[control-plane-memory] Import check passed')
PY

echo "[control-plane-memory] Running smoke flow"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

subprocess.run(['/workspace/ai-orchestrate', 'run', 'list files', '--trace'], check=True, capture_output=True, text=True)
subprocess.run(['/workspace/ai-orchestrate', 'run', "Create a file called hello.txt with content 'hi' and then list files", '--trace'], check=True, capture_output=True, text=True)

tl = subprocess.run(['/workspace/ai-orchestrate', 'memory-timeline', '/workspace/runs'], check=True, capture_output=True, text=True)
json.loads(tl.stdout)
rt = subprocess.run(['/workspace/ai-orchestrate', 'retrieve-memory', '/workspace/runs', 'list'], check=True, capture_output=True, text=True)
json.loads(rt.stdout)
cr = subprocess.run(['/workspace/ai-orchestrate', 'build-memory-corpus', '/workspace/runs'], check=True, capture_output=True, text=True)
json.loads(cr.stdout)

out = Path('/workspace/tmp/control-plane-memory-export')
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-memory-timeline', '/workspace/runs', str(out / 'timeline.md')], check=True, capture_output=True, text=True)
subprocess.run(['/workspace/ai-orchestrate', 'export-memory-timeline', '/workspace/runs', str(out / 'timeline.json')], check=True, capture_output=True, text=True)
print('[control-plane-memory] Smoke flow passed')
PY

echo "[control-plane-memory] PASS"
