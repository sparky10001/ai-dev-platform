#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.derived_purity import (
    DATASET_MODULE,
    audit_module_purity,
    audit_runtime_derived_purity,
    derived_purity_violations,
    validate_runtime_derived_purity,
)
from runtime.errors import EventLedgerError


class RuntimeDerivedPurityTests(unittest.TestCase):
    def _temp_module(self, code: str) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "mod.py"
        path.write_text(textwrap.dedent(code), encoding="utf-8")
        return path

    def test_core_derived_modules_pass_purity_audit(self) -> None:
        report = audit_runtime_derived_purity()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(derived_purity_violations(report), [])

    def test_open_write_detected(self) -> None:
        mod = self._temp_module(
            """
            def bad():
                with open('x.txt', 'w', encoding='utf-8') as f:
                    f.write('x')
            """
        )
        report = audit_module_purity(mod)
        self.assertTrue(any(v["symbol"] == "open" for v in report["violations"]))

    def test_path_write_text_detected(self) -> None:
        mod = self._temp_module(
            """
            from pathlib import Path
            def bad():
                Path('x.txt').write_text('x', encoding='utf-8')
            """
        )
        report = audit_module_purity(mod)
        self.assertTrue(any(v["symbol"].endswith("write_text") for v in report["violations"]))

    def test_os_remove_detected(self) -> None:
        mod = self._temp_module(
            """
            import os
            def bad():
                os.remove('x.txt')
            """
        )
        report = audit_module_purity(mod)
        self.assertTrue(any(v["symbol"] == "os.remove" for v in report["violations"]))

    def test_subprocess_run_detected(self) -> None:
        mod = self._temp_module(
            """
            import subprocess
            def bad():
                subprocess.run(['echo', 'x'])
            """
        )
        report = audit_module_purity(mod)
        self.assertTrue(any(v["type"] == "forbidden_subprocess" for v in report["violations"]))

    def test_runtime_engine_import_detected(self) -> None:
        mod = self._temp_module(
            """
            from runtime.engine import run_task
            """
        )
        report = audit_module_purity(mod)
        self.assertTrue(any(v["type"] == "forbidden_import" for v in report["violations"]))

    def test_datasets_classified_projection_writer(self) -> None:
        report = audit_runtime_derived_purity()
        self.assertEqual(report["classifications"][DATASET_MODULE], "projection_writer")
        dataset_modules = [m for m in report["modules"] if m["module"] == DATASET_MODULE]
        self.assertEqual(len(dataset_modules), 1)
        self.assertEqual(dataset_modules[0]["status"], "ok")

    def test_validate_runtime_derived_purity_raises_on_injected_violation(self) -> None:
        mod = self._temp_module(
            """
            def bad():
                with open('x.txt', 'w', encoding='utf-8') as f:
                    f.write('x')
            """
        )
        with patch("runtime.derived_purity.DEFAULT_DERIVED_MODULES", [str(mod)]):
            with self.assertRaises(EventLedgerError):
                validate_runtime_derived_purity()

    def test_cli_json_works(self) -> None:
        proc = subprocess.run(
            ["python3", "scripts/maintenance/derived_purity_audit.py", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("status", payload)
        self.assertIn("modules", payload)

    def test_cli_strict_exit_behavior(self) -> None:
        mod = self._temp_module(
            """
            def bad():
                with open('x.txt', 'w', encoding='utf-8') as f:
                    f.write('x')
            """
        )
        proc = subprocess.run(
            ["python3", "scripts/maintenance/derived_purity_audit.py", "--module", str(mod), "--strict"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
