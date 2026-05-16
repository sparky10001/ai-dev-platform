#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"

VOLATILE_KEYS = {
    "run_id",
    "run_path",
    "trace_path",
    "timestamp",
    "timestamps",
    "duration_ms",
    "created_at",
    "completed_at",
    "started_at",
    "ended_at",
}

RUN_PATH_RE = re.compile(r"/workspace/runs/run_[A-Za-z0-9_.-]+")
RUN_ID_RE = re.compile(r"run_[0-9A-Za-z_.-]+")


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(data: Any) -> str:
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        value = RUN_PATH_RE.sub("<RUN_PATH>", value)
        value = RUN_ID_RE.sub("<RUN_ID>", value)
    return value


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in VOLATILE_KEYS:
                normalized[key] = f"<{key.upper()}>"
            else:
                normalized[key] = normalize(item)
        return normalized

    if isinstance(value, list):
        return [normalize(item) for item in value]

    return _normalize_scalar(value)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_trace(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                raise AssertionError(f"Empty trace line at {line_no}")
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise AssertionError(f"Trace line {line_no} is not an object")
            events.append(event)
    return events


def _extract_latest_run_path(payload: dict[str, Any]) -> Path:
    meta = payload.get("meta") or {}
    run_path = meta.get("run_path")
    if not run_path:
        candidates = sorted(
            [p for p in RUNS_DIR.glob("run_*") if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
        )
        if not candidates:
            raise AssertionError("No run_path in result metadata and no run directories found")
        return candidates[-1]
    return Path(run_path)


def execute_snapshot_run() -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "AI_ADAPTER": "mock",
        "MODEL_PROVIDER": "mock",
    })

    proc = subprocess.run(
        [str(ROOT / "ai"), "run", "hello"],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        raise AssertionError(
            "ai run failed\n"
            f"returncode={proc.returncode}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}"
        )

    try:
        result_payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout is not JSON: {proc.stdout}") from exc

    run_path = _extract_latest_run_path(result_payload)
    result_path = run_path / "result.json"
    trace_path = run_path / "trace.jsonl"
    run_json_path = run_path / "run.json"

    if not result_path.exists():
        raise AssertionError(f"Missing result.json at {result_path}")
    if not trace_path.exists():
        raise AssertionError(f"Missing trace.jsonl at {trace_path}")

    result_json = _read_json(result_path)
    trace_events = _read_trace(trace_path)
    run_json = _read_json(run_json_path) if run_json_path.exists() else None

    return {
        "stdout": result_payload,
        "run_path": str(run_path),
        "result_json": result_json,
        "trace_events": trace_events,
        "run_json": run_json,
        "event_sequence": [event.get("event") for event in trace_events],
        "result_hash": _hash(normalize(result_json)),
        "trace_hash": _hash(normalize(trace_events)),
        "run_hash": _hash(normalize(run_json)) if run_json is not None else None,
    }


class RuntimeSnapshotTest(unittest.TestCase):
    def assert_success_status(self, payload: dict[str, Any]) -> None:
        status = payload.get("status")
        self.assertIn(
            status,
            {"done", "success"},
            f"Expected success-compatible status, got {status!r}: {payload}",
        )

    def assert_trace_shape(self, events: list[dict[str, Any]]) -> None:
        self.assertGreaterEqual(len(events), 3, "Trace should contain at least lifecycle events")

        sequence = [event.get("event") for event in events]
        self.assertEqual(sequence[0], "session_start", f"First event mismatch: {sequence}")
        self.assertEqual(sequence[-1], "session_end", f"Last event mismatch: {sequence}")
        self.assertIn("agent_output", sequence, f"agent_output missing: {sequence}")

    def test_runtime_snapshot_is_stable_across_two_runs(self) -> None:
        first = execute_snapshot_run()
        second = execute_snapshot_run()

        self.assert_success_status(first["stdout"])
        self.assert_success_status(second["stdout"])

        self.assert_trace_shape(first["trace_events"])
        self.assert_trace_shape(second["trace_events"])

        self.assertEqual(
            first["event_sequence"],
            second["event_sequence"],
            f"Trace event sequence drifted:\nfirst={first['event_sequence']}\nsecond={second['event_sequence']}",
        )

        self.assertEqual(
            first["result_hash"],
            second["result_hash"],
            f"Normalized result hash mismatch:\nfirst={first['run_path']}\nsecond={second['run_path']}",
        )

        self.assertEqual(
            first["trace_hash"],
            second["trace_hash"],
            f"Normalized trace hash mismatch:\nfirst={first['run_path']}\nsecond={second['run_path']}",
        )

        if first["run_hash"] is not None and second["run_hash"] is not None:
            self.assertEqual(
                first["run_hash"],
                second["run_hash"],
                f"Normalized run.json hash mismatch:\nfirst={first['run_path']}\nsecond={second['run_path']}",
            )


if __name__ == "__main__":
    unittest.main()
