#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from runtime.evals import evaluate_events, evaluate_run
from runtime.loader import RUNS_DIR
from runtime.registry import registry_summary_from_events, summarize_runs
from runtime.replay import replay_events, replay_trace, summarize_events
from runtime.trace_pipeline import append_trace_event


class RuntimeProjectionPurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "RUNTIME_REPLAY_SOURCE": os.environ.get("RUNTIME_REPLAY_SOURCE"),
            "RUNTIME_EVAL_SOURCE": os.environ.get("RUNTIME_EVAL_SOURCE"),
            "RUNTIME_REGISTRY_SOURCE": os.environ.get("RUNTIME_REGISTRY_SOURCE"),
            "RUNTIME_LEDGER_CANARY": os.environ.get("RUNTIME_LEDGER_CANARY"),
            "RUNTIME_LEDGER_AUTHORITATIVE": os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"),
        }
        for key in self._env:
            os.environ.pop(key, None)

        self.run_id = f"projection_purity_{os.getpid()}_{id(self)}"
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
        result_payload = {"status": "done", "output": "ok"}
        (self.run_dir / "run.json").write_text(json.dumps(run_payload) + "\n", encoding="utf-8")
        (self.run_dir / "result.json").write_text(json.dumps(result_payload) + "\n", encoding="utf-8")

        self.run = {
            "id": self.run_id,
            "run_path": str(self.run_dir),
            "trace_path": str(self.run_dir / "trace.jsonl"),
        }
        append_trace_event(self.run, "session_start", {"command": "run"})
        append_trace_event(self.run, "tool_call", "write_file", step=1, meta={"input": {"path": "a.txt"}})
        append_trace_event(self.run, "tool_result", "write_file", step=1, meta={"result": {"ok": True}})
        append_trace_event(self.run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(self.run, "session_end", {"status": "done"})

    def tearDown(self) -> None:
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def _in_memory_events(self):
        return [
            SimpleNamespace(
                schema_version=1,
                timestamp=1.0,
                run_id="inmem",
                event="session_start",
                data={"command": "hello"},
            ),
            SimpleNamespace(
                schema_version=1,
                timestamp=2.0,
                run_id="inmem",
                event="agent_output",
                data={"status": "done", "output": "ok"},
            ),
            SimpleNamespace(
                schema_version=1,
                timestamp=3.0,
                run_id="inmem",
                event="session_end",
                data={"status": "done"},
            ),
        ]

    def test_replay_projection_helper_from_memory(self) -> None:
        events = self._in_memory_events()
        replay = replay_events(events)
        self.assertEqual(replay.event_count, 3)
        self.assertEqual(replay.status, "done")
        self.assertTrue(replay.completed)

    def test_eval_projection_helper_from_memory(self) -> None:
        events = self._in_memory_events()
        summary = evaluate_events(events, run_id="inmem")
        self.assertEqual(summary.run_id, "inmem")
        self.assertEqual(summary.total_events, 3)
        self.assertEqual(summary.status, "done")

    def test_registry_projection_helper_from_memory(self) -> None:
        events = self._in_memory_events()
        summary = registry_summary_from_events(events, run_id="inmem")
        self.assertEqual(summary.total_runs, 1)
        self.assertEqual(summary.completed_runs, 1)
        self.assertEqual(summary.total_tool_calls, 0)

    def test_projection_helpers_do_not_require_files(self) -> None:
        events = self._in_memory_events()
        self.assertEqual(summarize_events(events)["events"], 3)
        self.assertEqual(evaluate_events(events, run_id="x").total_events, 3)
        self.assertEqual(registry_summary_from_events(events, run_id="x").total_runs, 1)

    def test_projection_helpers_match_public_run_apis(self) -> None:
        api_replay = replay_trace(self.run_dir / "trace.jsonl", strict=True, source="trace")
        api_eval = evaluate_run(self.run_id, source="trace")
        api_registry = summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="trace")

        events = replay_trace(self.run_dir / "trace.jsonl", strict=True, source="trace").events
        projection_replay = replay_events(events)
        projection_eval = evaluate_events(events, run_id=self.run_id, run={"created_at": 1.0, "completed_at": 4.0}, result={"status": "done"})
        projection_registry = registry_summary_from_events(
            events,
            run_id=self.run_id,
            run={"created_at": 1.0, "completed_at": 4.0},
            result={"status": "done"},
        )

        self.assertEqual(api_replay.event_count, projection_replay.event_count)
        self.assertEqual(api_eval.total_events, projection_eval.total_events)
        self.assertEqual(api_registry.total_runs, projection_registry.total_runs)

    def test_public_apis_use_canonical_event_loader(self) -> None:
        with patch("runtime.replay.load_runtime_events", wraps=__import__("runtime.replay", fromlist=["load_runtime_events"]).load_runtime_events) as replay_loader:
            replay_trace(self.run_dir / "trace.jsonl", strict=True, source="trace")
            self.assertGreaterEqual(replay_loader.call_count, 1)

        with patch("runtime.evals.load_runtime_events", wraps=__import__("runtime.evals", fromlist=["load_runtime_events"]).load_runtime_events) as eval_loader,              patch("runtime.evals.load_replay_events", wraps=__import__("runtime.evals", fromlist=["load_replay_events"]).load_replay_events) as eval_replay_loader:
            evaluate_run(self.run_id, source="trace")
            self.assertGreaterEqual(eval_loader.call_count + eval_replay_loader.call_count, 1)

        with patch("runtime.registry.load_runtime_events", wraps=__import__("runtime.registry", fromlist=["load_runtime_events"]).load_runtime_events) as registry_loader:
            summarize_runs(command=self.run_id, model=self.run_id, limit=1, source="trace")
            self.assertGreaterEqual(registry_loader.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
