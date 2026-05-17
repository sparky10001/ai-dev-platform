#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime.event_ledger import (
    audit_trace_dependencies,
    ledger_cutover_readiness,
    trace_compatibility_required,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerReadinessTests(unittest.TestCase):
    def _run(self, trace_path: Path, run_id: str = "run_test") -> dict:
        return {"id": run_id, "trace_path": str(trace_path), "run_path": str(trace_path.parent)}

    def test_readiness_success_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
            append_trace_event(run, "session_end", {"status": "done"})

            report = ledger_cutover_readiness(Path(td))
            self.assertTrue(report["trace_exists"])
            self.assertTrue(report["ledger_exists"])
            self.assertTrue(report["parity_valid"])
            self.assertTrue(report["replay_ledger_ready"])
            self.assertIn(report["status"], {"ready", "warning"})

    def test_readiness_detects_missing_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            (Path(td) / "ledger.jsonl").unlink()

            report = ledger_cutover_readiness(Path(td))
            self.assertFalse(report["ledger_exists"])
            self.assertIn("missing_ledger", report["errors"])
            self.assertEqual(report["status"], "blocked")

    def test_readiness_detects_parity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            ledger_path = Path(td) / "ledger.jsonl"
            lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            ledger_path.write_text(lines[0] + "\n", encoding="utf-8")

            report = ledger_cutover_readiness(Path(td))
            self.assertFalse(report["parity_valid"])
            self.assertEqual(report["status"], "blocked")

    def test_dependency_audit_structure(self) -> None:
        audit = audit_trace_dependencies()
        self.assertIn("status", audit)
        self.assertIn("dependencies", audit)
        self.assertIn("remaining_trace_dependencies", audit)
        self.assertIsInstance(audit["dependencies"], list)

    def test_authoritative_mode_readiness_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})

            prior = os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE")
            os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
            try:
                report = ledger_cutover_readiness(Path(td))
            finally:
                if prior is None:
                    os.environ.pop("RUNTIME_LEDGER_AUTHORITATIVE", None)
                else:
                    os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = prior

            self.assertTrue(report["authoritative_mode_available"])
            self.assertTrue(report["authoritative_mode_enabled"])

    def test_trace_compatibility_helper(self) -> None:
        self.assertTrue(trace_compatibility_required())


if __name__ == "__main__":
    unittest.main(verbosity=2)
