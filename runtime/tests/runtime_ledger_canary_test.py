#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.event_ledger import (
    evaluate_ledger_canary_readiness,
    ledger_canary_enabled,
    ledger_canary_environment,
    ledger_canary_parity_required,
    write_ledger_index,
)
from runtime.evals import eval_source, evaluate_run
from runtime.loader import RUNS_DIR
from runtime.registry import registry_source, summarize_runs
from runtime.replay import replay_source, replay_trace
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerCanaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "RUNTIME_LEDGER_CANARY": os.environ.get("RUNTIME_LEDGER_CANARY"),
            "RUNTIME_LEDGER_CANARY_PARITY_REQUIRED": os.environ.get("RUNTIME_LEDGER_CANARY_PARITY_REQUIRED"),
            "RUNTIME_LEDGER_AUTHORITATIVE": os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"),
            "RUNTIME_LEDGER_PARITY_REQUIRED": os.environ.get("RUNTIME_LEDGER_PARITY_REQUIRED"),
            "RUNTIME_REPLAY_SOURCE": os.environ.get("RUNTIME_REPLAY_SOURCE"),
            "RUNTIME_EVAL_SOURCE": os.environ.get("RUNTIME_EVAL_SOURCE"),
            "RUNTIME_REGISTRY_SOURCE": os.environ.get("RUNTIME_REGISTRY_SOURCE"),
            "AI_MAINTENANCE_ENABLED": os.environ.get("AI_MAINTENANCE_ENABLED"),
            "AI_MAINTENANCE_STAMP_PATH": os.environ.get("AI_MAINTENANCE_STAMP_PATH"),
        }
        for k in self._env:
            os.environ.pop(k, None)

        self.run_id = f"ledger_canary_test_{os.getpid()}_{id(self)}"
        self.run_dir = RUNS_DIR / self.run_id
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=False)

        run_payload = {
            "id": self.run_id,
            "status": "done",
            "created_at": 1.0,
            "completed_at": 3.0,
            "command": self.run_id,
            "model": self.run_id,
        }
        result_payload = {"status": "done", "output": "ok"}
        (self.run_dir / "run.json").write_text(json.dumps(run_payload) + "\n", encoding="utf-8")
        (self.run_dir / "result.json").write_text(json.dumps(result_payload) + "\n", encoding="utf-8")

        run = {
            "id": self.run_id,
            "run_path": str(self.run_dir),
            "trace_path": str(self.run_dir / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        write_ledger_index(self.run_dir)

    def tearDown(self) -> None:
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_canary_disabled_by_default(self) -> None:
        self.assertFalse(ledger_canary_enabled())

    def test_canary_enabled_by_env(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        self.assertTrue(ledger_canary_enabled())

    def test_canary_implies_ledger_default_sources(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        self.assertEqual(replay_source(), "ledger")
        self.assertEqual(eval_source(), "ledger")
        self.assertEqual(registry_source(), "ledger")

    def test_explicit_trace_override_still_wins(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        replay = replay_trace(self.run_dir / "trace.jsonl", strict=True, source="trace")
        ev = evaluate_run(self.run_id, source="trace")
        rg = summarize_runs(command=self.run_id, model=self.run_id, limit=1, sort_by="created_at", descending=True, source="trace")
        self.assertEqual(replay.event_count, 3)
        self.assertEqual(ev.total_events, 3)
        self.assertEqual(rg.total_runs, 1)

    def test_authoritative_and_canary_compatible(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        self.assertEqual(replay_source(), "ledger")
        self.assertEqual(eval_source(), "ledger")
        self.assertEqual(registry_source(), "ledger")

    def test_canary_parity_required_mapping(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        os.environ["RUNTIME_LEDGER_CANARY_PARITY_REQUIRED"] = "1"
        self.assertTrue(ledger_canary_parity_required())
        env = ledger_canary_environment()
        self.assertEqual(env["RUNTIME_LEDGER_PARITY_REQUIRED"], "1")

    def test_readiness_ready_path(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        os.environ["AI_MAINTENANCE_ENABLED"] = "1"
        os.environ["AI_MAINTENANCE_STAMP_PATH"] = str(self.run_dir / ".stamp")
        with patch("runtime.trace_compatibility.audit_trace_compatibility", return_value={"status": "ok", "summary": {"cutover_blocker_count": 0}}):
            report = evaluate_ledger_canary_readiness(self.run_dir)
        self.assertIn(report["status"], {"ready", "warning"})
        self.assertTrue(report["authoritative_effective"])

    def test_readiness_warning_when_canary_disabled(self) -> None:
        os.environ["AI_MAINTENANCE_ENABLED"] = "1"
        os.environ["AI_MAINTENANCE_STAMP_PATH"] = str(self.run_dir / ".stamp")
        with patch("runtime.trace_compatibility.audit_trace_compatibility", return_value={"status": "ok", "summary": {"cutover_blocker_count": 0}}):
            report = evaluate_ledger_canary_readiness(self.run_dir)
        self.assertEqual(report["status"], "warning")
        self.assertIn("canary_disabled", report["categories"])

    def test_readiness_blocked_on_drift(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        ledger_path = self.run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        ledger_path.write_text(lines[0] + "\n", encoding="utf-8")
        report = evaluate_ledger_canary_readiness(self.run_dir)
        self.assertEqual(report["status"], "blocked")

    def test_rollback_payload_deterministic(self) -> None:
        report = evaluate_ledger_canary_readiness(self.run_dir)
        self.assertEqual(
            report["rollback"]["unset"],
            [
                "RUNTIME_LEDGER_CANARY",
                "RUNTIME_LEDGER_AUTHORITATIVE",
                "RUNTIME_LEDGER_PARITY_REQUIRED",
                "RUNTIME_LEDGER_CANARY_PARITY_REQUIRED",
            ],
        )

    def test_cli_json_works(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_canary.py", str(self.run_dir), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("status", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        ledger_path = self.run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        ledger_path.write_text(lines[0] + "\n", encoding="utf-8")
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_canary.py", str(self.run_dir), "--strict"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)

    def test_cli_print_env(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/ledger_canary.py", "--print-env"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("export RUNTIME_LEDGER_CANARY=1", proc.stdout)
        self.assertIn("export RUNTIME_LEDGER_AUTHORITATIVE=1", proc.stdout)

    def test_summary_recent_limits_scan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td)
            for idx in range(4):
                run_dir = runs_root / f"run_{idx}"
                run_dir.mkdir(parents=True, exist_ok=False)
                run = {
                    "id": f"run_{idx}",
                    "run_path": str(run_dir),
                    "trace_path": str(run_dir / "trace.jsonl"),
                }
                append_trace_event(run, "session_start", {"command": "hello"})
                append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
                append_trace_event(run, "session_end", {"status": "done"})
                write_ledger_index(run_dir)
                os.utime(run_dir, (1000 + idx * 10, 1000 + idx * 10))

            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/ledger_canary.py",
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

    def test_no_authority_default_change_without_flags(self) -> None:
        self.assertEqual(replay_source(), "trace")
        self.assertEqual(eval_source(), "trace")
        self.assertEqual(registry_source(), "trace")


if __name__ == "__main__":
    unittest.main(verbosity=2)
