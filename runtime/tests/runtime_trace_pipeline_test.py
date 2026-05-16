#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime.errors import LifecycleOrderingError
from runtime.errors import NDJSONIntegrityError
from runtime.errors import TraceValidationError
from runtime.trace_pipeline import append_trace_event
from runtime.trace_pipeline import iter_trace_events
from runtime.trace_pipeline import load_trace
from runtime.trace_pipeline import validate_trace_file


class TracePipelineTests(unittest.TestCase):

    def make_run(self, path: Path):
        return {"id": "run_test", "trace_path": str(path)}

    def test_append_only_and_order(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            run = self.make_run(tp)
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
            append_trace_event(run, "session_end", {"status": "done"})
            lines = tp.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3)
            events = load_trace(tp, strict=True)
            self.assertEqual([e.event for e in events], ["session_start", "agent_output", "session_end"])

    def test_tolerant_mode_skips_malformed(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            tp.write_text("{bad}\n", encoding="utf-8")
            events = load_trace(tp, strict=False)
            self.assertEqual(events, [])

    def test_strict_mode_rejects_malformed(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            tp.write_text("{bad}\n", encoding="utf-8")
            with self.assertRaises(NDJSONIntegrityError):
                list(iter_trace_events(tp, strict=True))

    def test_strict_run_id_consistency(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            run = self.make_run(tp)
            append_trace_event(run, "session_start", {"command": "run"})
            text = tp.read_text(encoding="utf-8")
            text += text.replace("run_test", "other_run")
            tp.write_text(text, encoding="utf-8")
            with self.assertRaises(TraceValidationError):
                validate_trace_file(tp, strict=True)

    def test_lifecycle_ordering_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            run = self.make_run(tp)
            append_trace_event(run, "agent_output", {"status": "done", "output": "x"})
            append_trace_event(run, "session_end", {"status": "done"})
            with self.assertRaises(LifecycleOrderingError):
                validate_trace_file(tp, strict=True)

    def test_partial_trace_survives_tolerant(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            run = self.make_run(tp)
            append_trace_event(run, "session_start", {"command": "run"})
            events = load_trace(tp, strict=False)
            self.assertEqual(len(events), 1)

    def test_env_strict_toggle(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            tp.write_text("{bad}\n", encoding="utf-8")
            os.environ["RUNTIME_TRACE_STRICT"] = "1"
            try:
                with self.assertRaises(NDJSONIntegrityError):
                    validate_trace_file(tp)
            finally:
                os.environ.pop("RUNTIME_TRACE_STRICT", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)