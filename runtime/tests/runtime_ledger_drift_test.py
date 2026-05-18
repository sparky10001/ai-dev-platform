#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.errors import EventLedgerError
from runtime.ledger_drift import compare_trace_and_ledger, summarize_drift, validate_no_drift
from runtime.loader import RUNS_DIR
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self._run_id = f"drift_test_{os.getpid()}_{id(self)}"
        self._run_dir = RUNS_DIR / self._run_id
        if self._run_dir.exists():
            shutil.rmtree(self._run_dir)
        self._run_dir.mkdir(parents=True, exist_ok=False)

        run_payload = {
            "id": self._run_id,
            "status": "done",
            "created_at": 1.0,
            "completed_at": 2.0,
            "command": f"cmd_{self._run_id}",
            "model": f"model_{self._run_id}",
        }
        result_payload = {
            "schema_version": "response.v1",
            "status": "done",
            "output": "ok",
            "meta": {},
        }
        (self._run_dir / "run.json").write_text(json.dumps(run_payload) + "\n", encoding="utf-8")
        (self._run_dir / "result.json").write_text(json.dumps(result_payload) + "\n", encoding="utf-8")

        run = {
            "id": self._run_id,
            "run_path": str(self._run_dir),
            "trace_path": str(self._run_dir / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})

    def tearDown(self) -> None:
        if self._run_dir.exists():
            shutil.rmtree(self._run_dir)

    def test_matching_trace_ledger_passes(self) -> None:
        report = compare_trace_and_ledger(self._run_dir)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["drift_categories"], [])

    def test_missing_ledger_detected(self) -> None:
        (self._run_dir / "ledger.jsonl").unlink()
        report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("missing_ledger", report["drift_categories"])

    def test_missing_trace_detected(self) -> None:
        (self._run_dir / "trace.jsonl").unlink()
        report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("missing_trace", report["drift_categories"])

    def test_event_count_mismatch_detected(self) -> None:
        ledger_path = self._run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        ledger_path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
        report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("event_count_mismatch", report["drift_categories"])

    def test_event_hash_mismatch_detected(self) -> None:
        ledger_path = self._run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        payload = json.loads(lines[1])
        payload["data"] = {"status": "done", "output": "different"}
        lines[1] = json.dumps(payload)
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("event_hash_mismatch", report["drift_categories"])

    def test_replay_summary_mismatch_detected(self) -> None:
        with patch("runtime.ledger_drift.summarize_trace") as mocked:
            mocked.side_effect = [
                {"run_id": self._run_id, "events": 3, "status": "done", "output": "ok"},
                {"run_id": self._run_id, "events": 3, "status": "done", "output": "DIFF"},
            ]
            report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("replay_summary_mismatch", report["drift_categories"])

    def test_eval_summary_mismatch_detected(self) -> None:
        from runtime.schemas import EvalSummary

        with patch("runtime.ledger_drift.evaluate_run") as mocked:
            mocked.side_effect = [
                EvalSummary(
                    run_id=self._run_id,
                    status="done",
                    total_events=3,
                    tool_calls=0,
                    tool_results=0,
                    runtime_seconds=1.0,
                    completed=True,
                    replay_valid=True,
                    schema_valid=True,
                ),
                EvalSummary(
                    run_id=self._run_id,
                    status="error",
                    total_events=3,
                    tool_calls=0,
                    tool_results=0,
                    runtime_seconds=1.0,
                    completed=True,
                    replay_valid=True,
                    schema_valid=True,
                ),
            ]
            report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("eval_summary_mismatch", report["drift_categories"])

    def test_registry_summary_mismatch_detected(self) -> None:
        from runtime.schemas import RunSummary

        with patch("runtime.ledger_drift.summarize_runs") as mocked:
            mocked.side_effect = [
                RunSummary(total_runs=1, completed_runs=1, success_rate=1.0, average_runtime=1.0, total_tool_calls=0, replay_valid_runs=1, schema_valid_runs=1),
                RunSummary(total_runs=1, completed_runs=1, success_rate=0.0, average_runtime=1.0, total_tool_calls=0, replay_valid_runs=1, schema_valid_runs=1),
            ]
            report = compare_trace_and_ledger(self._run_dir)
        self.assertIn("registry_summary_mismatch", report["drift_categories"])

    def test_strict_validation_raises(self) -> None:
        (self._run_dir / "ledger.jsonl").unlink()
        with self.assertRaises(EventLedgerError):
            validate_no_drift(self._run_dir)

    def test_normalization_ignores_approved_volatile_fields(self) -> None:
        with patch("runtime.ledger_drift.summarize_trace") as mocked:
            mocked.side_effect = [
                {"run_id": self._run_id, "events": 3, "status": "done", "output": "ok", "timestamp": 1},
                {"run_id": self._run_id, "events": 3, "status": "done", "output": "ok", "timestamp": 2},
            ]
            report = compare_trace_and_ledger(self._run_dir)
        self.assertNotIn("replay_summary_mismatch", report["drift_categories"])

    def test_latest_run_audit_works(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_drift_audit.py", "--latest"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)

    def test_json_output_deterministic(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_drift_audit.py", str(self._run_dir), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("status", payload)
        self.assertIn("reports", payload)

    def test_strict_cli_exit_codes(self) -> None:
        (self._run_dir / "ledger.jsonl").unlink()
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_drift_audit.py", str(self._run_dir), "--strict"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)

        proc_error = subprocess.run(
            ["python3", "scripts/maintenance/ledger_drift_audit.py", "--latest", "--all"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_error.returncode, 2)

    def test_summary_shape(self) -> None:
        report = compare_trace_and_ledger(self._run_dir)
        summary = summarize_drift(report)
        self.assertIn("drift_detected", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
