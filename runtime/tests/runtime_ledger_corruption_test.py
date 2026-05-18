#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.errors import EventLedgerError
from runtime.event_ledger import write_ledger_index
from runtime.ledger_corruption import (
    classify_ledger_corruption,
    ledger_corruption_detected,
    recovery_guidance_for_categories,
    validate_no_ledger_corruption,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerCorruptionTests(unittest.TestCase):
    def _run(self, run_dir: Path, run_id: str = "run_test") -> dict[str, str]:
        return {
            "id": run_id,
            "run_path": str(run_dir),
            "trace_path": str(run_dir / "trace.jsonl"),
        }

    def _write_dual(self, run_dir: Path, run_id: str = "run_test") -> dict[str, str]:
        run = self._run(run_dir, run_id=run_id)
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        return run

    def test_clean_dual_written_run_reports_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            report = classify_ledger_corruption(run_dir)
            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["corruption_categories"], [])

    def test_missing_ledger_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "ledger.jsonl").unlink()
            report = classify_ledger_corruption(run_dir)
            self.assertIn("missing_ledger", report["corruption_categories"])

    def test_missing_trace_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "trace.jsonl").unlink()
            report = classify_ledger_corruption(run_dir)
            self.assertIn("missing_trace", report["corruption_categories"])

    def test_malformed_ledger_ndjson_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("malformed_ndjson", report["corruption_categories"])

    def test_empty_ledger_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "ledger.jsonl").write_text("", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("empty_ledger", report["corruption_categories"])

    def test_mixed_run_id_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            payload = json.loads(lines[-1])
            payload["run_id"] = "other"
            lines[-1] = json.dumps(payload)
            (run_dir / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("mixed_run_id", report["corruption_categories"])

    def test_mixed_schema_version_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            payload = json.loads(lines[-1])
            payload["schema_version"] = 2
            lines[-1] = json.dumps(payload)
            (run_dir / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("mixed_schema_version", report["corruption_categories"])

    def test_timestamp_regression_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            p0 = json.loads(lines[0])
            p1 = json.loads(lines[1])
            p2 = json.loads(lines[2])
            p1["timestamp"] = p0["timestamp"] - 1
            p2["timestamp"] = p1["timestamp"] - 1
            (run_dir / "ledger.jsonl").write_text(
                "\n".join([json.dumps(p0), json.dumps(p1), json.dumps(p2)]) + "\n", encoding="utf-8"
            )
            report = classify_ledger_corruption(run_dir)
            self.assertIn("timestamp_regression", report["corruption_categories"])

    def test_duplicate_lifecycle_events_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            lines.append(lines[0])
            (run_dir / "ledger.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("duplicate_lifecycle_event", report["corruption_categories"])

    def test_missing_lifecycle_event_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            filtered = [line for line in lines if json.loads(line).get("event") != "session_end"]
            (run_dir / "ledger.jsonl").write_text("\n".join(filtered) + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("missing_lifecycle_event", report["corruption_categories"])

    def test_event_after_session_end_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            reordered = [lines[0], lines[2], lines[1]]
            (run_dir / "ledger.jsonl").write_text("\n".join(reordered) + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("event_after_session_end", report["corruption_categories"])

    def test_parity_mismatch_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            (run_dir / "ledger.jsonl").write_text(lines[0] + "\n", encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("parity_mismatch", report["corruption_categories"])

    def test_index_mismatch_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            idx = write_ledger_index(run_dir)
            payload = json.loads(idx.read_text(encoding="utf-8"))
            payload["event_count"] = payload.get("event_count", 0) + 1
            idx.write_text(json.dumps(payload), encoding="utf-8")
            report = classify_ledger_corruption(run_dir)
            self.assertIn("index_mismatch", report["corruption_categories"])

    def test_replay_eval_registry_failure_categories_detected(self) -> None:
        runs_root = Path(__file__).resolve().parent.parent.parent / "runs"
        run_dir = runs_root / "run_corrupt"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))

        self._write_dual(run_dir, run_id="run_corrupt")
        (run_dir / "run.json").write_text(
            json.dumps({"id": "run_corrupt", "status": "done", "command": "x", "model": "m"}),
            encoding="utf-8",
        )
        (run_dir / "result.json").write_text(
            json.dumps({"status": "done", "output": "ok"}),
            encoding="utf-8",
        )
        with patch("runtime.ledger_corruption.replay_trace", side_effect=RuntimeError("bad replay")), \
             patch("runtime.ledger_corruption.evaluate_run", side_effect=RuntimeError("bad eval")), \
             patch("runtime.ledger_corruption.summarize_runs", side_effect=RuntimeError("bad reg")):
            report = classify_ledger_corruption(run_dir)
        self.assertIn("replay_failure", report["corruption_categories"])
        self.assertIn("eval_failure", report["corruption_categories"])
        self.assertIn("registry_failure", report["corruption_categories"])

    def test_recovery_guidance_deterministic(self) -> None:
        cats = ["parity_mismatch", "missing_ledger", "parity_mismatch"]
        guidance = recovery_guidance_for_categories(cats)
        self.assertEqual(guidance, sorted(guidance))

    def test_validate_no_ledger_corruption_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "ledger.jsonl").unlink()
            with self.assertRaises(EventLedgerError):
                validate_no_ledger_corruption(run_dir)

    def test_cli_json_works(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_corruption_audit.py", str(run_dir), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("status", payload)
            self.assertIn("reports", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            (run_dir / "ledger.jsonl").unlink()
            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_corruption_audit.py", str(run_dir), "--strict"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_latest_works(self) -> None:
        runs_root = Path(__file__).resolve().parent.parent.parent / "runs"
        run_dir = runs_root / "run_corruption_latest_test"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))
        self._write_dual(run_dir, run_id="run_corruption_latest_test")
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_corruption_audit.py", "--latest"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(proc.stdout.strip())

    def test_ledger_corruption_detected_helper(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir)
            report = classify_ledger_corruption(run_dir)
            self.assertFalse(ledger_corruption_detected(report))
            (run_dir / "ledger.jsonl").unlink()
            report2 = classify_ledger_corruption(run_dir)
            self.assertTrue(ledger_corruption_detected(report2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
