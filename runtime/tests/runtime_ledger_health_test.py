#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.errors import EventLedgerError
from runtime.event_ledger import write_ledger_index
from runtime.ledger_health import aggregate_ledger_health, ledger_health_report, validate_ledger_health
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerHealthTests(unittest.TestCase):
    def _run(self, run_dir: Path, run_id: str) -> dict[str, str]:
        return {
            "id": run_id,
            "run_path": str(run_dir),
            "trace_path": str(run_dir / "trace.jsonl"),
        }

    def _write_dual(self, run_dir: Path, run_id: str) -> dict[str, str]:
        run = self._run(run_dir, run_id)
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        write_ledger_index(run_dir)
        return run

    def _write_run_meta(self, run_dir: Path, run_id: str) -> None:
        (run_dir / "run.json").write_text(
            json.dumps({"id": run_id, "status": "done", "command": "hello", "model": "fast"}),
            encoding="utf-8",
        )
        (run_dir / "result.json").write_text(
            json.dumps({"status": "done", "output": "ok"}),
            encoding="utf-8",
        )

    def test_clean_run_reports_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")}, clear=False):
            run_dir = Path(td)
            self._write_dual(run_dir, "run_clean")
            report = ledger_health_report(run_dir)
            self.assertEqual(report["status"], "healthy")
            self.assertTrue(report["parity_ok"])

    def test_drifted_run_reports_warning_or_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_drift")
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            (run_dir / "ledger.jsonl").write_text(lines[0] + "\n", encoding="utf-8")
            report = ledger_health_report(run_dir)
            self.assertIn(report["status"], {"warning", "unhealthy"})
            self.assertTrue(report["drift_detected"])

    def test_corrupted_ledger_reports_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_corrupt")
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            report = ledger_health_report(run_dir)
            self.assertEqual(report["status"], "unhealthy")
            self.assertTrue(report["corruption_detected"])

    def test_missing_ledger_reports_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_missing_ledger")
            (run_dir / "ledger.jsonl").unlink()
            report = ledger_health_report(run_dir)
            self.assertEqual(report["status"], "warning")
            self.assertIn("missing_ledger", report["categories"])

    def test_missing_trace_reports_unhealthy_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_missing_trace")
            (run_dir / "trace.jsonl").unlink()
            report = ledger_health_report(run_dir)
            self.assertEqual(report["status"], "unhealthy")
            self.assertIn("missing_trace_required", report["categories"])

    def test_single_run_health_is_local_and_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            run_dir = Path(td) / "run_local"
            run_dir.mkdir(parents=True)
            self._write_dual(run_dir, "run_local")

            start = time.time()
            report = ledger_health_report(run_dir)
            elapsed = time.time() - start

            self.assertLess(elapsed, 2.0)
            self.assertIn(report["status"], {"healthy", "warning", "unhealthy"})

    def test_aggregate_summary_counts(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            runs = Path(td)
            r1 = runs / "run1"
            r1.mkdir()
            self._write_dual(r1, "run1")

            r2 = runs / "run2"
            r2.mkdir()
            self._write_dual(r2, "run2")
            (r2 / "ledger.jsonl").unlink()

            report = aggregate_ledger_health(runs)
            self.assertEqual(report["runs_scanned"], 2)
            self.assertGreaterEqual(report["healthy_runs"], 1)
            self.assertGreaterEqual(report["warning_runs"], 1)

    def test_maintenance_visibility_and_stale_detection(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {
                "AI_MAINTENANCE_ENABLED": "1",
                "AI_MAINTENANCE_INTERVAL_SEC": "10",
                "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp"),
            },
            clear=False,
        ):
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_maint")
            (Path(td) / ".stamp").write_text(str(time.time() - 1000), encoding="utf-8")
            report = ledger_health_report(run_dir)
            self.assertTrue(report["maintenance"]["maintenance_enabled"])
            self.assertTrue(report["maintenance"]["stale"])

    def test_cutover_readiness_integration(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_readiness")
            report = ledger_health_report(run_dir)
            self.assertIn("cutover_readiness", report)
            self.assertIn("ready", report["cutover_readiness"])

    def test_validate_ledger_health_raises_on_unhealthy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_validate")
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            with self.assertRaises(EventLedgerError):
                validate_ledger_health(run_dir)

    def test_cli_json_works(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_cli")
            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_health_report.py", str(run_dir), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("status", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self._write_dual(run_dir, "run_cli_strict")
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_health_report.py", str(run_dir), "--strict"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_latest_and_summary_work(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            run_dir = runs_root / "run_health_latest_test"
            run_dir.mkdir(parents=True, exist_ok=False)

            self._write_dual(run_dir, "run_health_latest_test")
            self._write_run_meta(run_dir, "run_health_latest_test")

            latest_proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_health_report.py",
                    "--latest",
                    "--runs-root",
                    str(runs_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(latest_proc.returncode, 0)
            self.assertTrue(latest_proc.stdout.strip())

            summary_proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_health_report.py",
                    "--summary",
                    "--json",
                    "--runs-root",
                    str(runs_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(summary_proc.returncode, 0)
            payload = json.loads(summary_proc.stdout)
            self.assertIn("runs_scanned", payload)

    def test_summary_recent_limits_scan_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            run_ids = ["run_recent_a", "run_recent_b", "run_recent_c"]
            base = time.time() - 100
            for idx, run_id in enumerate(run_ids):
                run_dir = runs_root / run_id
                run_dir.mkdir(parents=True, exist_ok=False)
                self._write_dual(run_dir, run_id)
                self._write_run_meta(run_dir, run_id)
                ts = base + idx
                os.utime(run_dir, (ts, ts))

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_health_report.py",
                    "--summary",
                    "--json",
                    "--recent",
                    "2",
                    "--runs-root",
                    str(runs_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("runs_scanned"), 2)
            ids = [item.get("run_id") for item in payload.get("reports", [])]
            self.assertEqual(ids, ["run_recent_c", "run_recent_b"])

    def test_summary_recent_zero_scans_zero_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            run_dir = runs_root / "run_zero"
            run_dir.mkdir(parents=True, exist_ok=False)
            self._write_dual(run_dir, "run_zero")
            self._write_run_meta(run_dir, "run_zero")

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_health_report.py",
                    "--summary",
                    "--json",
                    "--recent",
                    "0",
                    "--runs-root",
                    str(runs_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("runs_scanned"), 0)
            self.assertEqual(payload.get("reports"), [])

    def test_summary_recent_negative_rejected(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "scripts/maintenance/ledger_health_report.py",
                "--summary",
                "--recent",
                "-1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)

    def test_latest_unaffected_by_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            run_dir = runs_root / "run_latest_recent"
            run_dir.mkdir(parents=True, exist_ok=False)
            self._write_dual(run_dir, "run_latest_recent")
            self._write_run_meta(run_dir, "run_latest_recent")

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_health_report.py",
                    "--latest",
                    "--recent",
                    "0",
                    "--runs-root",
                    str(runs_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("run_latest_recent", proc.stdout)



if __name__ == "__main__":
    unittest.main(verbosity=2)
