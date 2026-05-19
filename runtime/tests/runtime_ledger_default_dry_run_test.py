#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.event_ledger import (
    evaluate_ledger_default_readiness,
    ledger_default_dry_run_enabled,
    write_ledger_index,
)
from runtime.evals import eval_source
from runtime.registry import registry_source
from runtime.replay import replay_source
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerDefaultDryRunTests(unittest.TestCase):
    def _run(self, run_dir: Path, run_id: str) -> dict[str, str]:
        return {
            "id": run_id,
            "run_path": str(run_dir),
            "trace_path": str(run_dir / "trace.jsonl"),
        }

    def _write_dual(self, run_dir: Path, run_id: str) -> None:
        run = self._run(run_dir, run_id)
        append_trace_event(run, "session_start", {"command": "hello"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        write_ledger_index(run_dir)

    def test_dry_run_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            self.assertFalse(ledger_default_dry_run_enabled())

    def test_env_flag_enables_dry_run_mode(self) -> None:
        with patch.dict("os.environ", {"RUNTIME_LEDGER_DRY_RUN_DEFAULT": "1"}, clear=False):
            self.assertTrue(ledger_default_dry_run_enabled())

    def test_healthy_run_reports_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {
                "RUNTIME_LEDGER_DRY_RUN_DEFAULT": "1",
                "AI_MAINTENANCE_ENABLED": "1",
                "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp"),
            },
            clear=False,
        ):
            run_dir = Path(td) / "run_ready"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_ready")
            with patch("runtime.trace_compatibility.audit_trace_compatibility", return_value={"status": "ok", "summary": {"cutover_blocker_count": 0}}):
                report = evaluate_ledger_default_readiness(run_dir)
            self.assertEqual(report["status"], "ready")
            self.assertTrue(report["parity_ok"])

    def test_drift_reports_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            run_dir = Path(td) / "run_drift"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_drift")
            lines = (run_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            (run_dir / "ledger.jsonl").write_text(lines[0] + "\n", encoding="utf-8")
            report = evaluate_ledger_default_readiness(run_dir)
            self.assertEqual(report["status"], "blocked")
            self.assertIn("drift_detected", report["categories"])

    def test_corruption_reports_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run_corrupt"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_corrupt")
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            report = evaluate_ledger_default_readiness(run_dir)
            self.assertEqual(report["status"], "blocked")
            self.assertIn("corruption_detected", report["categories"])

    def test_cutover_blockers_report_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run_blockers"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_blockers")
            with patch("runtime.trace_compatibility.audit_trace_compatibility", return_value={"status": "blocked", "summary": {"cutover_blocker_count": 2}}):
                report = evaluate_ledger_default_readiness(run_dir)
            self.assertEqual(report["status"], "blocked")
            self.assertIn("trace_blockers_present", report["categories"])

    def test_compatibility_warning_not_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            run_dir = Path(td) / "run_warn"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_warn")
            with patch("runtime.trace_compatibility.audit_trace_compatibility", return_value={"status": "warning", "summary": {"cutover_blocker_count": 0}}):
                report = evaluate_ledger_default_readiness(run_dir)
            self.assertEqual(report["status"], "warning")
            self.assertIn("compatibility_warning", report["categories"])

    def test_cli_json_and_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            run_dir = runs_root / "run_cli"
            run_dir.mkdir()
            self._write_dual(run_dir, "run_cli")

            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_default_dry_run.py", str(run_dir), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("status", payload)

            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            strict_proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_default_dry_run.py", str(run_dir), "--strict"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(strict_proc.returncode, 1)

    def test_summary_aggregation_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            runs_root = Path(td)
            run_a = runs_root / "run_a"
            run_a.mkdir()
            self._write_dual(run_a, "run_a")

            run_b = runs_root / "run_b"
            run_b.mkdir()
            self._write_dual(run_b, "run_b")
            (run_b / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")

            proc = subprocess.run(
                ["python3", "scripts/maintenance/ledger_default_dry_run.py", "--summary", "--json", "--runs-root", str(runs_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["runs_scanned"], 2)
            self.assertGreaterEqual(payload["blocked_runs"], 1)


    def test_summary_recent_limits_scan(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(
            "os.environ",
            {"AI_MAINTENANCE_ENABLED": "1", "AI_MAINTENANCE_STAMP_PATH": str(Path(td) / ".stamp")},
            clear=False,
        ):
            runs_root = Path(td)
            base = time.time() - 1000

            for idx in range(4):
                run_dir = runs_root / f"run_{idx}"
                run_dir.mkdir()
                self._write_dual(run_dir, f"run_{idx}")
                ts = base + (idx * 10)
                os.utime(run_dir, (ts, ts))

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_default_dry_run.py",
                    "--summary",
                    "--json",
                    "--runs-root",
                    str(runs_root),
                    "--recent",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["runs_scanned"], 2)
            scanned = []
            for report in payload.get("reports", []):
                details = report.get("details", {})
                path = (
                    details.get("cutover_readiness", {}).get("run_path")
                    or details.get("ledger_health_report", {})
                    .get("details", {})
                    .get("cutover_readiness", {})
                    .get("run_path", "")
                )
                scanned.append(path)
            self.assertTrue(any("run_3" in path for path in scanned), msg=str(scanned))
            self.assertTrue(any("run_2" in path for path in scanned), msg=str(scanned))

    def test_dry_run_does_not_change_authority_defaults(self) -> None:
        with patch.dict("os.environ", {"RUNTIME_LEDGER_DRY_RUN_DEFAULT": "1"}, clear=False):
            self.assertEqual(replay_source(), "trace")
            self.assertEqual(eval_source(), "trace")
            self.assertEqual(registry_source(), "trace")


if __name__ == "__main__":
    unittest.main(verbosity=2)
