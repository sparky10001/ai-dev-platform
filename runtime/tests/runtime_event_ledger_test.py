#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime.errors import EventLedgerError, TraceValidationError
from runtime.event_ledger import (
    append_event,
    build_ledger_index,
    canonical_event_payload,
    event_hash,
    iter_ledger_events,
    ledger_path_for_run,
    load_ledger,
    load_ledger_index,
    validate_ledger_file,
    validate_trace_ledger_parity,
    write_ledger_index,
)
from runtime.trace_pipeline import append_trace_event


class RuntimeEventLedgerTests(unittest.TestCase):

    def _run(self, trace_path: Path, run_id: str = "run_test") -> dict:
        return {"id": run_id, "trace_path": str(trace_path), "run_path": str(trace_path.parent)}

    def _event(self, *, ts: float = 1.0, name: str = "session_start", run_id: str = "run_test", data: dict | None = None) -> dict:
        return {
            "schema_version": 1,
            "timestamp": ts,
            "run_id": run_id,
            "event": name,
            "data": data if data is not None else {},
        }

    def test_ledger_path_derives_from_trace_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = {"trace_path": str(Path(td) / "trace.jsonl")}
            self.assertEqual(ledger_path_for_run(run), Path(td) / "ledger.jsonl")

    def test_append_load_iter_validate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_event(run, self._event(ts=1.0, name="session_start", data={"command": "run"}))
            append_event(run, self._event(ts=2.0, name="agent_output", data={"status": "done", "output": "ok"}))
            append_event(run, self._event(ts=3.0, name="session_end", data={"status": "done"}))
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
                json.dumps(self._event(ts=1.0, run_id="run_a")),
                json.dumps({"schema_version": 2, "timestamp": 2.0, "run_id": "run_b", "event": "session_end", "data": {}}),
            ]
            ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(TraceValidationError):
                validate_ledger_file(run, strict=True)

    def test_canonical_event_payload_deterministic_output(self) -> None:
        event = {
            "event": "session_start",
            "data": {"x": 1},
            "run_id": "run_test",
            "timestamp": 1.25,
            "schema_version": 1,
            "extra": "ignored",
        }
        expected = {
            "schema_version": 1,
            "run_id": "run_test",
            "event": "session_start",
            "timestamp": 1.25,
            "data": {"x": 1},
        }
        self.assertEqual(canonical_event_payload(event), expected)

    def test_event_hash_stable_for_equivalent_dict_ordering(self) -> None:
        a = {"schema_version": 1, "run_id": "r", "event": "e", "timestamp": 1.0, "data": {"a": 1, "b": 2}}
        b = {"timestamp": 1.0, "event": "e", "run_id": "r", "data": {"b": 2, "a": 1}, "schema_version": 1}
        self.assertEqual(event_hash(a), event_hash(b))

    def test_event_hash_changes_when_payload_changes(self) -> None:
        a = self._event(data={"v": 1})
        b = self._event(data={"v": 2})
        self.assertNotEqual(event_hash(a), event_hash(b))

    def test_build_ledger_index_deterministic_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_event(run, self._event(ts=1.0, name="session_start"))
            append_event(run, self._event(ts=2.0, name="agent_output", data={"output": "ok", "status": "done"}))
            idx1 = build_ledger_index(run)
            idx2 = build_ledger_index(run)
            self.assertEqual(idx1, idx2)
            self.assertEqual(idx1["event_count"], 2)

    def test_write_load_ledger_index_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_event(run, self._event(ts=1.0, name="session_start"))
            append_event(run, self._event(ts=2.0, name="session_end"))
            path = write_ledger_index(run)
            self.assertTrue(path.exists())
            loaded = load_ledger_index(run)
            rebuilt = build_ledger_index(run)
            self.assertEqual(loaded, rebuilt)

    def test_ledger_hash_stable_across_repeated_builds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_event(run, self._event(ts=1.0, name="session_start"))
            append_event(run, self._event(ts=2.0, name="session_end"))
            self.assertEqual(build_ledger_index(run)["ledger_hash"], build_ledger_index(run)["ledger_hash"])

    def test_validate_trace_ledger_parity_succeeds_for_dual_written_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "agent_output", {"status": "done", "output": "ok"})
            append_trace_event(run, "session_end", {"status": "done"})
            report = validate_trace_ledger_parity(run, strict=True)
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["errors"], [])

    def test_parity_detects_event_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            ledger_path = Path(td) / "ledger.jsonl"
            ledger_lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            ledger_path.write_text(ledger_lines[0] + "\n", encoding="utf-8")
            report = validate_trace_ledger_parity(run)
            self.assertIn("event_count_mismatch", report["errors"])

    def test_parity_detects_event_sequence_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            ledger_path = Path(td) / "ledger.jsonl"
            lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            ledger_path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
            report = validate_trace_ledger_parity(run)
            self.assertIn("event_sequence_mismatch", report["errors"])

    def test_parity_detects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            ledger_path = Path(td) / "ledger.jsonl"
            lines = [json.loads(x) for x in ledger_path.read_text(encoding="utf-8").strip().splitlines()]
            lines[1]["data"] = {"status": "different"}
            ledger_path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
            report = validate_trace_ledger_parity(run)
            self.assertIn("hash_sequence_mismatch", report["errors"])

    def test_strict_parity_raises_event_ledger_error_on_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            append_trace_event(run, "session_start", {"command": "run"})
            append_trace_event(run, "session_end", {"status": "done"})
            ledger_path = Path(td) / "ledger.jsonl"
            ledger_lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
            ledger_path.write_text(ledger_lines[0] + "\n", encoding="utf-8")
            with self.assertRaises(EventLedgerError):
                validate_trace_ledger_parity(run, strict=True)

    def test_validate_ledger_file_rejects_empty_ledger_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            (Path(td) / "ledger.jsonl").write_text("", encoding="utf-8")
            with self.assertRaises(TraceValidationError):
                validate_ledger_file(run, strict=True)

    def test_validate_ledger_file_rejects_timestamp_regression_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = self._run(Path(td) / "trace.jsonl")
            ledger = Path(td) / "ledger.jsonl"
            lines = [
                json.dumps(self._event(ts=2.0, name="session_start")),
                json.dumps(self._event(ts=1.0, name="session_end")),
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
