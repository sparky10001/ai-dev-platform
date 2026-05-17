#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from runtime.replay import load_replay_events, replay_source, replay_trace, summarize_trace
from runtime.trace_pipeline import append_trace_event


class RuntimeReplayLedgerTests(unittest.TestCase):

    def setUp(self) -> None:
        self._original_replay_source = os.environ.get("RUNTIME_REPLAY_SOURCE")
        os.environ.pop("RUNTIME_REPLAY_SOURCE", None)

    def tearDown(self) -> None:
        if self._original_replay_source is None:
            os.environ.pop("RUNTIME_REPLAY_SOURCE", None)
        else:
            os.environ["RUNTIME_REPLAY_SOURCE"] = self._original_replay_source

    def _run(self, trace_path: Path, run_id: str = "run_test") -> dict:
        return {
            "id": run_id,
            "trace_path": str(trace_path),
            "run_path": str(trace_path.parent),
        }

    def _dual_write_run(self, base: Path) -> dict:
        run = self._run(base / "trace.jsonl")
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})
        return run

    def test_default_replay_source_is_trace(self) -> None:
        os.environ.pop("RUNTIME_REPLAY_SOURCE", None)
        self.assertEqual(replay_source(), "trace")

    def test_invalid_replay_source_env_is_deterministic(self) -> None:
        os.environ["RUNTIME_REPLAY_SOURCE"] = "invalid-source"
        try:
            self.assertEqual(replay_source(), "trace")
        finally:
            os.environ.pop("RUNTIME_REPLAY_SOURCE", None)

    def test_env_var_ledger_selects_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            os.environ["RUNTIME_REPLAY_SOURCE"] = "ledger"
            try:
                replay = replay_trace(Path(run["trace_path"]))
            finally:
                os.environ.pop("RUNTIME_REPLAY_SOURCE", None)
            self.assertEqual(replay.event_count, 3)
            self.assertEqual(replay.run_id, "run_test")

    def test_explicit_source_ledger_loads_ledger_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            events = load_replay_events(Path(run["trace_path"]), source="ledger", strict=True)
            self.assertEqual([evt.event for evt in events], ["session_start", "agent_output", "session_end"])

    def test_missing_ledger_in_ledger_mode_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            trace_path.write_text("", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_replay_events(trace_path, source="ledger", strict=True)

    def test_replay_from_ledger_matches_trace_event_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            trace_replay = replay_trace(Path(run["trace_path"]), strict=True, source="trace")
            ledger_replay = replay_trace(Path(run["trace_path"]), strict=True, source="ledger")
            self.assertEqual([e.event for e in trace_replay.events], [e.event for e in ledger_replay.events])

    def test_replay_summaries_equivalent_for_trace_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            trace_replay = replay_trace(Path(run["trace_path"]), strict=True, source="trace")
            ledger_replay = replay_trace(Path(run["trace_path"]), strict=True, source="ledger")
            trace_summary = summarize_trace(Path(run["trace_path"]), source="trace")
            ledger_summary = summarize_trace(Path(run["trace_path"]), source="ledger")

            self.assertEqual(trace_replay.run_id, ledger_replay.run_id)
            self.assertEqual(trace_replay.status, ledger_replay.status)
            self.assertEqual(trace_replay.output, ledger_replay.output)
            self.assertEqual(trace_replay.event_count, ledger_replay.event_count)
            self.assertEqual(trace_replay.events[0].event, ledger_replay.events[0].event)
            self.assertEqual(trace_replay.events[-1].event, ledger_replay.events[-1].event)

            self.assertEqual(trace_summary["run_id"], ledger_summary["run_id"])
            self.assertEqual(trace_summary["status"], ledger_summary["status"])
            self.assertEqual(trace_summary["output"], ledger_summary["output"])
            self.assertEqual(trace_summary["events"], ledger_summary["events"])

    def test_trace_replay_behavior_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._dual_write_run(Path(td))
            replay = replay_trace(Path(run["trace_path"]), strict=True, source="trace")
            self.assertTrue(replay.started)
            self.assertTrue(replay.completed)
            self.assertEqual(replay.event_count, 3)
            self.assertEqual([evt.event for evt in replay.events], ["session_start", "agent_output", "session_end"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
