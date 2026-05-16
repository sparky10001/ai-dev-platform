#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime.errors import LifecycleOrderingError
from runtime.errors import NDJSONIntegrityError
from runtime.errors import ReplayCorruptionError
from runtime.errors import TraceValidationError
from runtime.trace_pipeline import append_trace_event
from runtime.trace_pipeline import iter_trace_events
from runtime.trace_pipeline import load_trace
from runtime.trace_pipeline import validate_trace_file
from runtime.trace_pipeline import ingest_trace_events


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

    def test_ingest_trace_events_preserves_valid_events_and_reports_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"

            diagnostics = ingest_trace_events(
                tp,
                [
                    {
                        "schema_version": 1,
                        "run_id": "run_test",
                        "event": "session_start",
                        "timestamp": 1.0,
                        "data": {"command": "run"},
                    },
                    {"bad": "missing event"},
                    {
                        "schema_version": 1,
                        "run_id": "run_test",
                        "event": "agent_output",
                        "timestamp": 2.0,
                        "data": {"status": "done", "output": "ok"},
                    },
                    {
                        "schema_version": 1,
                        "run_id": "run_test",
                        "event": "session_end",
                        "timestamp": 3.0,
                        "data": {"status": "done"},
                    },
                ],
                strict=False,
            )

            self.assertTrue(tp.exists(), "ingest_trace_events should persist valid trace events")
            events = load_trace(tp, strict=False)
            self.assertEqual(
                [event.event for event in events],
                ["session_start", "agent_output", "session_end"],
            )
            self.assertEqual(len(diagnostics), 1)
            self.assertEqual(diagnostics[0]["index"], 1)
            self.assertEqual(diagnostics[0]["error_type"], "ValueError")

    def test_ingest_trace_events_strict_raises_typed_error(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            with self.assertRaises(ReplayCorruptionError):
                ingest_trace_events(
                    tp,
                    [
                        {
                            "schema_version": 1,
                            "run_id": "run_test",
                            "event": "session_start",
                            "timestamp": 1.0,
                            "data": {"command": "run"},
                        },
                        {"bad": "missing event"},
                    ],
                    strict=True,
                )

    def test_rejects_timestamp_regression_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 2.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 1.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}])
            with self.assertRaises(TraceValidationError):
                validate_trace_file(tp, strict=True)

    def test_rejects_mixed_schema_version_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 2, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}])
            with self.assertRaises(TraceValidationError):
                validate_trace_file(tp, strict=True)

    def test_rejects_duplicate_session_start_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.1, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}])
            with self.assertRaises(LifecycleOrderingError):
                validate_trace_file(tp, strict=True)

    def test_rejects_duplicate_session_end_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.1, "data": {"status": "done"}}])
            with self.assertRaises(LifecycleOrderingError):
                validate_trace_file(tp, strict=True)

    def test_rejects_duplicate_agent_output_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.1, "data": {"status": "done", "output": "ok2"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}])
            with self.assertRaises(LifecycleOrderingError):
                validate_trace_file(tp, strict=True)

    def test_rejects_event_after_session_end_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 4.0, "data": {"command": "run"}}])
            with self.assertRaises(LifecycleOrderingError):
                validate_trace_file(tp, strict=True)

    def test_accepts_valid_deterministic_lifecycle_trace_strict(self):
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td) / "trace.jsonl"
            ingest_trace_events(tp, [{"schema_version": 1, "run_id": "run_test", "event": "session_start", "timestamp": 1.0, "data": {"command": "run"}}, {"schema_version": 1, "run_id": "run_test", "event": "agent_output", "timestamp": 2.0, "data": {"status": "done", "output": "ok"}}, {"schema_version": 1, "run_id": "run_test", "event": "session_end", "timestamp": 3.0, "data": {"status": "done"}}])
            validated = validate_trace_file(tp, strict=True)
            self.assertEqual(len(validated), 3)


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