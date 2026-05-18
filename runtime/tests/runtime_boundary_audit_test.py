#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.boundary_audit import (
    BOUNDARY_RULES,
    audit_import_boundaries,
    audit_runtime_boundaries,
    boundary_violations,
    validate_runtime_boundaries,
)
from runtime.errors import EventLedgerError


class RuntimeBoundaryAuditTests(unittest.TestCase):
    def test_current_repo_boundary_audit_passes(self) -> None:
        report = audit_runtime_boundaries()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(boundary_violations(report), [])

    def _mk(self, td: str, rel: str, content: str) -> Path:
        path = Path(td) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        return path

    def test_forbidden_runtime_engine_import_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/replay.py", "from runtime.engine import run_task\n")
            report = audit_import_boundaries(td)
            self.assertTrue(any(v["import"].startswith("runtime.engine") for v in report["violations"]))

    def test_event_ledger_importing_replay_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/event_ledger.py", "import runtime.replay\n")
            report = audit_import_boundaries(td)
            self.assertTrue(any(v["module"] == "runtime/event_ledger.py" for v in report["violations"]))

    def test_trace_pipeline_importing_registry_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/trace_pipeline.py", "from runtime.registry import summarize_runs\n")
            report = audit_import_boundaries(td)
            self.assertTrue(any(v["module"] == "runtime/trace_pipeline.py" for v in report["violations"]))

    def test_replay_importing_adapter_gateway_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/replay.py", "import runtime.adapter_gateway\n")
            report = audit_import_boundaries(td)
            self.assertTrue(any(v["module"] == "runtime/replay.py" for v in report["violations"]))

    def test_control_plane_importing_runtime_engine_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "control-plane/core/x.py", "import runtime.engine\n")
            report = audit_import_boundaries(td)
            self.assertTrue(any(v["module"].startswith("control-plane") for v in report["violations"]))

    def test_allowed_event_ledger_import_from_derived_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/replay.py", "from runtime.event_ledger import load_ledger\n")
            self._mk(td, "runtime/evals.py", "from runtime.event_ledger import load_ledger\n")
            self._mk(td, "runtime/registry.py", "from runtime.event_ledger import load_ledger\n")
            report = audit_import_boundaries(td)
            self.assertEqual(report["status"], "ok")

    def test_cli_json_works(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/runtime_boundary_audit.py", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("status", payload)
        self.assertIn("modules", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mod = self._mk(td, "runtime/replay.py", "from runtime.engine import run_task\n")
            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/runtime_boundary_audit.py",
                    "--module",
                    str(mod),
                    "--strict",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)

    def test_validate_runtime_boundaries_raises_on_injected_violation(self) -> None:
        patched = dict(BOUNDARY_RULES)
        patched["runtime/replay.py"] = {"forbidden_imports": {"runtime.engine"}}

        with tempfile.TemporaryDirectory() as td:
            self._mk(td, "runtime/replay.py", "from runtime.engine import run_task\n")
            with patch("runtime.boundary_audit.BOUNDARY_RULES", patched):
                with patch(
                    "runtime.boundary_audit.audit_runtime_boundaries",
                    return_value=audit_import_boundaries(td),
                ):
                    with self.assertRaises(EventLedgerError):
                        validate_runtime_boundaries()


if __name__ == "__main__":
    unittest.main(verbosity=2)
