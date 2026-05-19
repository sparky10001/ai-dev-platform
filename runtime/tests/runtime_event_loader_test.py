#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime.evals import eval_source
from runtime.event_loader import (
    iter_runtime_events,
    load_runtime_events,
    resolve_runtime_event_source,
    runtime_event_source,
)
from runtime.registry import registry_source
from runtime.replay import replay_source
from runtime.trace_pipeline import append_trace_event


class RuntimeEventLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "RUNTIME_LEDGER_AUTHORITATIVE": os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"),
            "RUNTIME_LEDGER_CANARY": os.environ.get("RUNTIME_LEDGER_CANARY"),
            "RUNTIME_EVENT_SOURCE": os.environ.get("RUNTIME_EVENT_SOURCE"),
            "RUNTIME_REPLAY_SOURCE": os.environ.get("RUNTIME_REPLAY_SOURCE"),
            "RUNTIME_EVAL_SOURCE": os.environ.get("RUNTIME_EVAL_SOURCE"),
            "RUNTIME_REGISTRY_SOURCE": os.environ.get("RUNTIME_REGISTRY_SOURCE"),
        }
        for key in self._env:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _dual_write_run(self, base: Path, run_id: str = "run_loader") -> dict:
        run = {
            "id": run_id,
            "run_path": str(base),
            "trace_path": str(base / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "hello"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        return run

    def test_default_source_is_trace(self) -> None:
        self.assertEqual(runtime_event_source(), "trace")

    def test_authoritative_flag_resolves_ledger(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        self.assertEqual(runtime_event_source(), "ledger")

    def test_canary_flag_resolves_ledger(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        self.assertEqual(runtime_event_source(), "ledger")

    def test_explicit_source_trace_wins(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        self.assertEqual(resolve_runtime_event_source("trace"), "trace")

    def test_explicit_source_ledger_wins(self) -> None:
        self.assertEqual(resolve_runtime_event_source("ledger"), "ledger")

    def test_invalid_explicit_source_falls_back_deterministically(self) -> None:
        self.assertEqual(resolve_runtime_event_source("bogus"), "trace")

    def test_invalid_env_source_fallback_trace_safe(self) -> None:
        os.environ["RUNTIME_EVENT_SOURCE"] = "bogus"
        self.assertEqual(runtime_event_source(), "trace")

    def test_load_runtime_events_reads_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            events = load_runtime_events(run["trace_path"], source="trace", strict=True)
            self.assertEqual([evt.event for evt in events], ["session_start", "agent_output", "session_end"])

    def test_load_runtime_events_reads_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            events = load_runtime_events(run["trace_path"], source="ledger", strict=True)
            self.assertEqual([evt.event for evt in events], ["session_start", "agent_output", "session_end"])

    def test_iter_runtime_events_streams_trace_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            trace_events = list(iter_runtime_events(run["trace_path"], source="trace", strict=True))
            ledger_events = list(iter_runtime_events(run["trace_path"], source="ledger", strict=True))
            self.assertEqual([e.event for e in trace_events], [e.event for e in ledger_events])

    def test_missing_ledger_in_ledger_mode_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            trace_path.write_text("", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_runtime_events(trace_path, source="ledger", strict=True)

    def test_replay_eval_registry_helpers_delegate_consistently(self) -> None:
        os.environ["RUNTIME_LEDGER_CANARY"] = "1"
        self.assertEqual(replay_source(), "ledger")
        self.assertEqual(eval_source(), "ledger")
        self.assertEqual(registry_source(), "ledger")

    def test_trace_ledger_parity_identical_for_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            trace_events = load_runtime_events(run["trace_path"], source="trace", strict=True)
            ledger_events = load_runtime_events(run["trace_path"], source="ledger", strict=True)
            self.assertEqual(len(trace_events), len(ledger_events))
            self.assertEqual([evt.event for evt in trace_events], [evt.event for evt in ledger_events])

    def test_no_circular_import_regression(self) -> None:
        from runtime import evals, registry, replay  # noqa: F401
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
