#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime.errors import EventLedgerError, TraceValidationError
from runtime.event_ledger import append_event, iter_ledger_events, ledger_path_for_run, load_ledger, validate_ledger_file
from runtime.trace_pipeline import append_trace_event


class RuntimeEventLedgerTests(unittest.TestCase):

    def _run(self, trace_path: Path) -> dict:
        return {"id": "run_test", "trace_path": str(trace_path), "run_path": str(trace_path.parent)}

    def test_ledger_path_derives_from_trace_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = {"trace_path": str(Path(td) / "trace.jsonl")}
            self.assertEqual(ledger_path_for_run(run), Path(td) / "ledger.jsonl")

    def test_append_load_iter_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_event(run, {"schema_version": 1, "timestamp": 1.0, "run_id": "run_test", "event": "session_start", "data": {"command": "run"}})
            append_event(run, {"schema_version": 1, "timestamp": 2.0, "run_id": "run_test", "event": "agent_output", "data": {"status": "done", "output": "ok"}})
            append_event(run, {"schema_version": 1, "timestamp": 3.0, "run_id": "run_test", "event": "session_end", "data": {"status": "done"}})
            loaded = load_ledger(run, strict=True)
            itered = list(iter_ledger_events(run, strict=True))
            self.assertEqual([e.event for e in loaded], ["session_start", "agent_output", "session_end"])
            self.assertEqual([e.event for e in itered], ["session_start", "agent_output", "session_end"])
            self.assertEqual(len(validate_ledger_file(run, strict=True)), 3)

    def test_validate_ledger_rejects_mixed_run_id_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            ledger = Path(td) / "ledger.jsonl"
            lines = [
                json.dumps({"schema_version": 1, "timestamp": 1.0, "run_id": "run_a", "event": "session_start", "data": {}}),
                json.dumps({"schema_version": 2, "timestamp": 2.0, "run_id": "run_b", "event": "session_end", "data": {}}),
            ]
            ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(TraceValidationError):
                validate_ledger_file(run, strict=True)

    def test_dual_write_from_append_trace_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
            append_trace_event(run, "session_end", {"status": "done"})
            trace_lines = (Path(td) / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
            ledger_lines = (Path(td) / "ledger.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(trace_lines), 3)
            self.assertEqual(len(ledger_lines), 3)

    def test_ledger_failure_modes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            os.environ.pop("RUNTIME_LEDGER_STRICT", None)
            with mock.patch("runtime.trace_pipeline.append_ledger_event", side_effect=RuntimeError("ledger down")):
                append_trace_event(run, "session_start", {"command": "run"})
            os.environ["RUNTIME_LEDGER_STRICT"] = "1"
            try:
                with mock.patch("runtime.trace_pipeline.append_ledger_event", side_effect=RuntimeError("ledger down")):
                    with self.assertRaises(EventLedgerError):
                        append_trace_event(run, "session_start", {"command": "run"})
            finally:
                os.environ.pop("RUNTIME_LEDGER_STRICT", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
