#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from runtime.default_authority_simulation import (
    build_default_authority_simulation,
    default_authority_simulation_blockers,
    evaluate_default_authority_simulation,
)
from runtime.event_ledger import write_ledger_index
from runtime.trace_pipeline import append_trace_event


class RuntimeDefaultAuthoritySimulationTests(unittest.TestCase):
    def _make_run(self, root: Path, run_id: str) -> Path:
        run_dir = root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        run = {"id": run_id, "run_path": str(run_dir), "trace_path": str(run_dir / "trace.jsonl")}
        append_trace_event(run, "session_start", {"command": "hello"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        write_ledger_index(run_dir)
        return run_dir

    def _patched_deps(
        self,
        *,
        matrix_status: str = "ready",
        dual_status: str = "ready",
        compat_blockers: int = 0,
        drift: bool = False,
        corruption: bool = False,
        replay_status: str = "ready",
        evals_status: str = "ready",
        registry_status: str = "ready",
        rollback_supported: bool = True,
        candidates: int = 0,
        retained: int = 0,
    ):
        matrix = {
            "status": matrix_status,
            "decision": {"recommended_mode": "trace", "cutover_ready": matrix_status == "ready", "ledger_default_safe": matrix_status == "ready"},
            "warnings": ["compatibility_warning"] if matrix_status == "warning" else [],
            "matrix": {
                "drift": {"status": "blocked" if drift else "ready", "detected": drift},
                "corruption": {"status": "blocked" if corruption else "ready", "detected": corruption},
                "replay": {"status": replay_status},
                "evals": {"status": evals_status},
                "registry": {"status": registry_status},
                "compatibility": {"status": "blocked" if compat_blockers else "ok", "summary": {"cutover_blocker_count": compat_blockers}, "cutover_blockers": [{}] * compat_blockers},
                "rollback": {"supported": rollback_supported, "method": "env_unset", "commands": ["unset RUNTIME_LEDGER_CANARY"]},
            },
        }
        dual = {
            "status": dual_status,
            "warnings": ["dual_validation_inactive"] if dual_status == "warning" else [],
            "validation": {"rollback": {"supported": rollback_supported, "method": "env_unset", "commands": ["unset RUNTIME_LEDGER_CANARY"]}},
        }
        transition = {
            "current_default": "trace",
            "effective_mode": "trace",
            "canary_enabled": False,
            "authoritative_enabled": False,
            "dry_run_enabled": False,
            "default_cutover_performed": False,
            "trace_emission_enabled": True,
            "rollback_supported": rollback_supported,
            "rollback_method": "env_unset",
            "rollback_unset": ["RUNTIME_LEDGER_CANARY", "RUNTIME_LEDGER_AUTHORITATIVE"],
        }
        inventory = {
            "status": "informational",
            "summary": {"total_references": 1},
            "candidates": [{"path": "docs/x.md"}] * candidates,
            "retained": [{"path": "runtime/event_loader.py"}] * retained,
            "operational": [],
        }

        stack = ExitStack()
        stack.enter_context(patch("runtime.default_authority_simulation.evaluate_ledger_authority_readiness", return_value=matrix))
        stack.enter_context(patch("runtime.default_authority_simulation.evaluate_dual_authority_validation", return_value=dual))
        stack.enter_context(patch("runtime.default_authority_simulation.runtime_authority_transition_state", return_value=transition))
        stack.enter_context(patch("runtime.default_authority_simulation.build_trace_deprecation_inventory", return_value=inventory))
        return stack

    def test_ready_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_ready")
            with self._patched_deps():
                report = evaluate_default_authority_simulation(run_dir)
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["simulation"]["actual_default"], "trace")
            self.assertEqual(report["simulation"]["simulated_default"], "ledger")
            self.assertFalse(report["simulation"]["authority_switch_performed"])

    def test_warning_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_warning")
            with self._patched_deps(matrix_status="warning", dual_status="warning", candidates=1, retained=1):
                report = evaluate_default_authority_simulation(run_dir)
            self.assertEqual(report["status"], "warning")
            self.assertIn("safe for simulation", report["recommendations"])

    def test_blocked_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_blocked")
            with self._patched_deps(compat_blockers=1, drift=True):
                report = evaluate_default_authority_simulation(run_dir)
            self.assertEqual(report["status"], "blocked")
            self.assertTrue(report["blockers"])
            self.assertIn("not safe for default cutover", report["recommendations"])

    def test_deterministic_blocker_ordering(self) -> None:
        payload = {
            "validation": {
                "drift": {"detected": True},
                "corruption": {"detected": True},
                "compatibility": {"status": "blocked"},
                "replay": {"status": "blocked"},
                "evals": {"status": "blocked"},
                "registry": {"status": "blocked"},
                "control_plane": {"status": "blocked"},
                "authority_matrix": {"status": "blocked"},
                "dual_validation": {"status": "blocked"},
            },
            "rollback": {"supported": False},
        }
        blockers = default_authority_simulation_blockers(payload)
        self.assertEqual(blockers, sorted(blockers, key=lambda item: (item["code"], item["area"], item["message"])))

    def test_simulation_never_changes_authority_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_no_switch")
            before = os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE")
            with self._patched_deps():
                _ = evaluate_default_authority_simulation(run_dir)
            self.assertEqual(os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"), before)

    def test_rollover_and_governance_propagation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_props")
            with self._patched_deps(rollback_supported=True):
                report = evaluate_default_authority_simulation(run_dir)
            self.assertTrue(report["rollback"]["supported"])
            self.assertIn("authority_matrix", report["validation"])
            self.assertIn("dual_validation", report["validation"])
            self.assertIn("compatibility", report["validation"])
            self.assertIn("deprecation_inventory", report["validation"])

    def test_summary_recent_limiting(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = 1000
            for idx in range(4):
                run_dir = self._make_run(root, f"run_{idx}")
                os.utime(run_dir, (base + idx * 10, base + idx * 10))
            with self._patched_deps():
                report = build_default_authority_simulation(None, runs_root=root, recent=2)
            self.assertEqual(report["runs_scanned"], 2)

    def test_cli_json_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._make_run(root, "run_cli_json")
            proc = subprocess.run(
                ["python3", "scripts/maintenance/default_authority_simulation.py", "--latest", "--json", "--runs-root", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            payload = json.loads(proc.stdout)
            self.assertIn("simulation", payload)
            self.assertIn("validation", payload)

    def test_cli_strict_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = self._make_run(root, "run_cli_strict")
            (run_dir / "ledger.jsonl").write_text("{bad}\n", encoding="utf-8")
            proc = subprocess.run(
                ["python3", "scripts/maintenance/default_authority_simulation.py", "--latest", "--strict", "--runs-root", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_no_runtime_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run(Path(td), "run_no_mut")
            trace_before = (run_dir / "trace.jsonl").read_text(encoding="utf-8")
            ledger_before = (run_dir / "ledger.jsonl").read_text(encoding="utf-8")
            _ = evaluate_default_authority_simulation(run_dir)
            self.assertEqual((run_dir / "trace.jsonl").read_text(encoding="utf-8"), trace_before)
            self.assertEqual((run_dir / "ledger.jsonl").read_text(encoding="utf-8"), ledger_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
