#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import unittest
from pathlib import Path

from runtime.errors import EventLedgerError
from runtime.evals import eval_source, evaluate_run
from runtime.loader import RUNS_DIR
from runtime.registry import registry_source, summarize_runs
from runtime.replay import replay_source, replay_trace
from runtime.trace_pipeline import append_trace_event


class RuntimeLedgerAuthoritativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "RUNTIME_LEDGER_AUTHORITATIVE": os.environ.get("RUNTIME_LEDGER_AUTHORITATIVE"),
            "RUNTIME_LEDGER_PARITY_REQUIRED": os.environ.get("RUNTIME_LEDGER_PARITY_REQUIRED"),
            "RUNTIME_REPLAY_SOURCE": os.environ.get("RUNTIME_REPLAY_SOURCE"),
            "RUNTIME_EVAL_SOURCE": os.environ.get("RUNTIME_EVAL_SOURCE"),
            "RUNTIME_REGISTRY_SOURCE": os.environ.get("RUNTIME_REGISTRY_SOURCE"),
        }
        for k in self._env:
            os.environ.pop(k, None)

        self.run_id = f"ledger_auth_test_{os.getpid()}_{id(self)}"
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

        run = {
            "id": self.run_id,
            "run_path": str(self.run_dir),
            "trace_path": str(self.run_dir / "trace.jsonl"),
        }
        append_trace_event(run, "session_start", {"command": "run"})
        append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
        append_trace_event(run, "session_end", {"status": "done"})

    def tearDown(self) -> None:
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)

    def test_default_behavior_unchanged(self) -> None:
        self.assertEqual(replay_source(), "trace")
        self.assertEqual(eval_source(), "trace")
        self.assertEqual(registry_source(), "trace")

    def test_authoritative_flag_switches_defaults(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        self.assertEqual(replay_source(), "ledger")
        self.assertEqual(eval_source(), "ledger")
        self.assertEqual(registry_source(), "ledger")

    def test_explicit_source_override_still_works(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        replay = replay_trace(self.run_dir / "trace.jsonl", strict=True, source="trace")
        ev = evaluate_run(self.run_id, source="trace")
        rg = summarize_runs(command=self.run_id, model=self.run_id, limit=1, sort_by="created_at", descending=True, source="trace")
        self.assertEqual(replay.event_count, 3)
        self.assertEqual(ev.total_events, 3)
        self.assertEqual(rg.total_runs, 1)

    def test_parity_enforcement_disabled_by_default(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        ledger_path = self.run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        ledger_path.write_text(lines[0] + "\n", encoding="utf-8")

        replay = replay_trace(self.run_dir / "trace.jsonl", strict=True)
        ev = evaluate_run(self.run_id)
        rg = summarize_runs(command=self.run_id, model=self.run_id, limit=1, sort_by="created_at", descending=True)

        self.assertEqual(replay.event_count, 1)
        self.assertEqual(ev.total_events, 1)
        self.assertEqual(rg.total_runs, 1)

    def test_parity_enforcement_enabled_mismatch_raises(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        os.environ["RUNTIME_LEDGER_PARITY_REQUIRED"] = "1"

        ledger_path = self.run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
        ledger_path.write_text(lines[0] + "\n", encoding="utf-8")

        with self.assertRaises(EventLedgerError):
            replay_trace(self.run_dir / "trace.jsonl", strict=True)
        with self.assertRaises(EventLedgerError):
            evaluate_run(self.run_id)
        with self.assertRaises(EventLedgerError):
            summarize_runs(command=self.run_id, model=self.run_id, limit=1, sort_by="created_at", descending=True)

    def test_parity_success_path(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        os.environ["RUNTIME_LEDGER_PARITY_REQUIRED"] = "1"

        replay = replay_trace(self.run_dir / "trace.jsonl", strict=True)
        ev = evaluate_run(self.run_id)
        rg = summarize_runs(command=self.run_id, model=self.run_id, limit=1, sort_by="created_at", descending=True)

        self.assertEqual(replay.event_count, 3)
        self.assertEqual(ev.total_events, 3)
        self.assertEqual(rg.total_runs, 1)

    def test_trace_artifacts_still_emitted(self) -> None:
        self.assertTrue((self.run_dir / "trace.jsonl").exists())
        self.assertTrue((self.run_dir / "ledger.jsonl").exists())

    def test_missing_ledger_deterministic_failure(self) -> None:
        os.environ["RUNTIME_LEDGER_AUTHORITATIVE"] = "1"
        (self.run_dir / "ledger.jsonl").unlink()
        with self.assertRaises(RuntimeError):
            replay_trace(self.run_dir / "trace.jsonl", strict=True)
        with self.assertRaises(RuntimeError):
            evaluate_run(self.run_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
