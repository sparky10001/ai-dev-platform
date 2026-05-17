#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path

from runtime.loader import RUNS_DIR
from runtime.registry import (
    load_registry_events,
    registry_source,
    summarize_runs,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeRegistryLedgerTests(unittest.TestCase):

    def setUp(self) -> None:
        self._orig_registry_source = os.environ.get("RUNTIME_REGISTRY_SOURCE")
        os.environ.pop("RUNTIME_REGISTRY_SOURCE", None)

        self.run_id = f"registry_ledger_test_{os.getpid()}_{id(self)}"
        self.run_dir = RUNS_DIR / self.run_id
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=False)

        run_payload = {
            "id": self.run_id,
            "status": "done",
            "created_at": 1.0,
            "completed_at": 4.0,
            "command": self.run_id,
            "model": self.run_id,
        }
        result_payload = {
            "status": "done",
            "output": "ok",
        }

        (self.run_dir / "run.json").write_text(json.dumps(run_payload) + "\n", encoding="utf-8")
        (self.run_dir / "result.json").write_text(json.dumps(result_payload) + "\n", encoding="utf-8")

        run = {
            "id": self.run_id,
            "run_path": str(self.run_dir),
            "trace_path": str(self.run_dir / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "tool_call", "write_file", step=1, meta={"input": {"path": "a.txt"}})
        append_trace_event(run, "tool_result", "write_file", step=1, meta={"result": {"ok": True}})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})

    def tearDown(self) -> None:
        if self._orig_registry_source is None:
            os.environ.pop("RUNTIME_REGISTRY_SOURCE", None)
        else:
            os.environ["RUNTIME_REGISTRY_SOURCE"] = self._orig_registry_source
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_default_registry_source_is_trace(self) -> None:
        self.assertEqual(registry_source(), "trace")

    def test_invalid_registry_source_env_is_deterministic(self) -> None:
        os.environ["RUNTIME_REGISTRY_SOURCE"] = "invalid"
        self.assertEqual(registry_source(), "trace")

    def test_env_var_ledger_selection(self) -> None:
        os.environ["RUNTIME_REGISTRY_SOURCE"] = "ledger"
        summary = summarize_runs(command=self.run_id, model=self.run_id, limit=1)
        self.assertEqual(summary.total_runs, 1)

    def test_explicit_source_ledger(self) -> None:
        summary = summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="ledger")
        self.assertEqual(summary.total_runs, 1)

    def test_missing_ledger_deterministic_error(self) -> None:
        ledger_path = self.run_dir / "ledger.jsonl"
        if ledger_path.exists():
            ledger_path.unlink()
        with self.assertRaises(RuntimeError):
            load_registry_events(self.run_dir, source="ledger")

    def test_trace_ledger_registry_parity_for_dual_written_run(self) -> None:
        trace_summary = summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="trace")
        ledger_summary = summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="ledger")

        self.assertEqual(trace_summary.total_runs, ledger_summary.total_runs)
        self.assertEqual(trace_summary.completed_runs, ledger_summary.completed_runs)
        self.assertEqual(trace_summary.total_tool_calls, ledger_summary.total_tool_calls)
        self.assertEqual(trace_summary.replay_valid_runs, ledger_summary.replay_valid_runs)
        self.assertEqual(trace_summary.schema_valid_runs, ledger_summary.schema_valid_runs)

    def test_registry_event_counts_and_lifecycle_match(self) -> None:
        trace_events = load_registry_events(self.run_dir, source="trace")
        ledger_events = load_registry_events(self.run_dir, source="ledger")

        self.assertEqual(len(trace_events), len(ledger_events))
        self.assertEqual(trace_events[0].event, ledger_events[0].event)
        self.assertEqual(trace_events[-1].event, ledger_events[-1].event)
        self.assertEqual(sum(1 for e in trace_events if e.event == "tool_call"), sum(1 for e in ledger_events if e.event == "tool_call"))
        self.assertEqual(sum(1 for e in trace_events if e.event == "tool_result"), sum(1 for e in ledger_events if e.event == "tool_result"))

    def test_existing_trace_registry_behavior_unchanged(self) -> None:
        summary = summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="trace")
        self.assertEqual(summary.total_runs, 1)
        self.assertEqual(summary.completed_runs, 1)
        self.assertEqual(summary.total_tool_calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
