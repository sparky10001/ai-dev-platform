#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from runtime.trace_compatibility import (
    audit_trace_compatibility,
    classify_trace_dependency,
    summarize_trace_dependencies,
    validate_trace_cutover_readiness,
)


class RuntimeTraceCompatibilityTests(unittest.TestCase):
    def test_repo_audit_runs(self) -> None:
        report = audit_trace_compatibility(".")
        self.assertIn(report["status"], {"ok", "warning", "blocked"})
        self.assertIn("categories", report)
        self.assertIn("cutover_blockers", report)

    def test_compatibility_only_not_flagged_as_blocker(self) -> None:
        dep = classify_trace_dependency("runtime/replay.py", content='x="trace.jsonl"\ny="ledger.jsonl"\n')
        self.assertEqual(dep["classification"], "compatibility_only")

    def test_operational_tooling_not_flagged_as_blocker(self) -> None:
        dep = classify_trace_dependency("scripts/maintenance/foo.py", content='trace.jsonl\n')
        self.assertEqual(dep["classification"], "operational_tooling")

    def test_true_runtime_hard_dependency_flagged_as_blocker(self) -> None:
        dep = classify_trace_dependency(
            "runtime/source_gate.py",
            content='TRACE_PATH = "trace.jsonl"\nopen(TRACE_PATH, "r", encoding="utf-8")\n',
        )
        self.assertEqual(dep["classification"], "cutover_blocker")

    def test_blocker_downgrade_classification_works(self) -> None:
        dep = classify_trace_dependency("runtime/engine.py", content='from runtime.trace_pipeline import ingest_trace_events\n')
        self.assertEqual(dep["classification"], "compatibility_only")

    def test_test_only_classification(self) -> None:
        dep = classify_trace_dependency("runtime/tests/test_x.py", content='load_trace("trace.jsonl")\n')
        self.assertEqual(dep["classification"], "test_only")

    def test_documentation_only_classification(self) -> None:
        dep = classify_trace_dependency("docs/runtime.md", content='trace.jsonl source of truth\n')
        self.assertEqual(dep["classification"], "documentation_only")

    def test_summary_counts_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "runtime").mkdir()
            (root / "scripts" / "maintenance").mkdir(parents=True)
            (root / "docs").mkdir()
            (root / "runtime" / "hard.py").write_text('x="trace.jsonl"\n', encoding="utf-8")
            (root / "scripts" / "maintenance" / "a.py").write_text('x="trace.jsonl"\n', encoding="utf-8")
            (root / "docs" / "a.md").write_text('trace.jsonl\n', encoding="utf-8")

            report = audit_trace_compatibility(root)
            summary = summarize_trace_dependencies(report)
            self.assertEqual(summary["total_dependencies"], 3)
            self.assertEqual(summary["summary"]["cutover_blocker_count"], 1)
            self.assertEqual(summary["summary"]["operational_tooling_count"], 1)
            self.assertEqual(summary["summary"]["documentation_only_count"], 1)
            self.assertEqual(len(summary["cutover_blockers"]), 1)

    def test_validate_trace_cutover_readiness_raises_on_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "runtime").mkdir()
            (root / "scripts").mkdir()
            (root / "control-plane").mkdir()
            (root / "docs").mkdir()
            (root / "runtime" / "hard.py").write_text('x="trace.jsonl"\n', encoding="utf-8")
            try:
                from runtime import trace_compatibility as tc

                original = tc.audit_trace_compatibility
                tc.audit_trace_compatibility = lambda _root=".": audit_trace_compatibility(root)
                with self.assertRaises(RuntimeError):
                    validate_trace_cutover_readiness()
            finally:
                tc.audit_trace_compatibility = original

    def test_cli_json_works(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/trace_compatibility_audit.py", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("status", payload)
        self.assertIn("cutover_blockers", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "runtime").mkdir()
            (root / "scripts").mkdir()
            (root / "control-plane").mkdir()
            (root / "docs").mkdir()
            (root / "runtime" / "hard.py").write_text('x="trace.jsonl"\n', encoding="utf-8")
            proc = subprocess.run(
                [
                    "python3",
                    "scripts/maintenance/trace_compatibility_audit.py",
                    "--strict",
                    "--root",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
