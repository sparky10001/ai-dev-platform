#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from runtime.evals import eval_source, evaluate_run, load_eval_events
from runtime.loader import RUNS_DIR
from runtime.replay import replay_trace, summarize_trace
from runtime.trace_pipeline import append_trace_event


class RuntimeEvalLedgerTests(unittest.TestCase):

    def setUp(self) -> None:
        self._orig_eval_source = os.environ.get("RUNTIME_EVAL_SOURCE")
        os.environ.pop("RUNTIME_EVAL_SOURCE", None)
        self._tmp = tempfile.TemporaryDirectory()
        self._run_id = f"eval_ledger_test_{os.getpid()}_{id(self)}"
        self._run_dir = RUNS_DIR / self._run_id
        if self._run_dir.exists():
            shutil.rmtree(self._run_dir)
        self._run_dir.mkdir(parents=True, exist_ok=False)

        run_payload = {
            "id": self._run_id,
            "status": "done",
            "created_at": 1.0,
            "completed_at": 4.0,
        }
        result_payload = {
            "status": "done",
            "output": "ok",
        }
        (self._run_dir / "run.json").write_text(json.dumps(run_payload) + "\n", encoding="utf-8")
        (self._run_dir / "result.json").write_text(json.dumps(result_payload) + "\n", encoding="utf-8")

        run = {
            "id": self._run_id,
            "run_path": str(self._run_dir),
            "trace_path": str(self._run_dir / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})

    def tearDown(self) -> None:
        if self._orig_eval_source is None:
            os.environ.pop("RUNTIME_EVAL_SOURCE", None)
        else:
            os.environ["RUNTIME_EVAL_SOURCE"] = self._orig_eval_source
        if self._run_dir.exists():
            shutil.rmtree(self._run_dir)
        self._tmp.cleanup()

    def test_default_eval_source_is_trace(self) -> None:
        self.assertEqual(eval_source(), "trace")

    def test_invalid_eval_source_env_is_deterministic(self) -> None:
        os.environ["RUNTIME_EVAL_SOURCE"] = "invalid"
        self.assertEqual(eval_source(), "trace")

    def test_env_var_ledger_selection(self) -> None:
        os.environ["RUNTIME_EVAL_SOURCE"] = "ledger"
        summary = evaluate_run(self._run_id)
        self.assertEqual(summary.run_id, self._run_id)
        self.assertEqual(summary.total_events, 3)

    def test_explicit_source_ledger(self) -> None:
        summary = evaluate_run(self._run_id, source="ledger")
        self.assertEqual(summary.run_id, self._run_id)
        self.assertEqual(summary.total_events, 3)

    def test_missing_ledger_deterministic_error(self) -> None:
        ledger_path = self._run_dir / "ledger.jsonl"
        if ledger_path.exists():
            ledger_path.unlink()
        with self.assertRaises(RuntimeError):
            evaluate_run(self._run_id, source="ledger")

    def test_trace_ledger_evaluation_parity_for_dual_written_run(self) -> None:
        trace_eval = evaluate_run(self._run_id, source="trace")
        ledger_eval = evaluate_run(self._run_id, source="ledger")

        self.assertEqual(trace_eval.run_id, ledger_eval.run_id)
        self.assertEqual(trace_eval.status, ledger_eval.status)
        self.assertEqual(trace_eval.total_events, ledger_eval.total_events)
        self.assertEqual(trace_eval.completed, ledger_eval.completed)
        self.assertEqual(trace_eval.tool_calls, ledger_eval.tool_calls)
        self.assertEqual(trace_eval.tool_results, ledger_eval.tool_results)

        trace_replay = replay_trace(self._run_dir / "trace.jsonl", strict=True, source="trace")
        ledger_replay = replay_trace(self._run_dir / "trace.jsonl", strict=True, source="ledger")
        self.assertEqual(trace_replay.output, ledger_replay.output)

        trace_summary = summarize_trace(self._run_dir / "trace.jsonl", source="trace")
        ledger_summary = summarize_trace(self._run_dir / "trace.jsonl", source="ledger")
        self.assertEqual(trace_summary["started"], ledger_summary["started"])
        self.assertEqual(trace_summary["completed"], ledger_summary["completed"])
        self.assertEqual(trace_summary["output"], ledger_summary["output"])

    def test_existing_trace_evaluation_behavior_unchanged(self) -> None:
        summary = evaluate_run(self._run_id, source="trace")
        self.assertEqual(summary.run_id, self._run_id)
        self.assertEqual(summary.status, "done")
        self.assertEqual(summary.total_events, 3)
        self.assertTrue(summary.completed)

    def test_load_eval_events_ledger(self) -> None:
        events = load_eval_events(self._run_dir, source="ledger")
        self.assertEqual([evt.event for evt in events], ["session_start", "agent_output", "session_end"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
