#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.evals.evaluator import evaluate_replay
from core.memory.corpora import build_memory_corpus
from core.memory.exporter import export_memory_corpus_json
from core.memory.exporter import export_memory_timeline_json
from core.memory.exporter import export_memory_timeline_markdown
from core.memory.history import build_memory_timeline
from core.memory.history import replay_to_memory_record
from core.memory.retrieval import retrieve_memory_records
from core.memory.timelines import reconstruct_execution_timeline
from core.memory.timelines import summarize_memory_timeline
from core.orchestrator.orchestrator import orchestrate_task
from core.replay.loader import load_orchestration_trace


class OrchestrationMemoryTests(unittest.TestCase):

    def _records(self):
        a = orchestrate_task({'task': 'list files', 'trace': True})
        b = orchestrate_task({'task': "Create a file called hello.txt with content 'hi' and then list files", 'trace': True})
        ra = load_orchestration_trace(a.run_path)
        rb = load_orchestration_trace(b.run_path)
        ea = evaluate_replay(ra)
        eb = evaluate_replay(rb)
        return [replay_to_memory_record(ra, ea), replay_to_memory_record(rb, eb)]

    def test_memory_record_generation(self):
        records = self._records()
        self.assertTrue(records[0].memory_id)

    def test_timeline_ordering_and_reconstruction(self):
        records = self._records()
        tl = build_memory_timeline(records, timeline_id='t1')
        rec = reconstruct_execution_timeline(records)
        self.assertEqual([r.run_id for r in tl.records], [r.run_id for r in rec])

    def test_retrieval_matching(self):
        records = self._records()
        q1 = retrieve_memory_records(records, 'success')
        self.assertGreaterEqual(q1.total_matches, 1)

        q2 = retrieve_memory_records(records, 'deterministic')
        self.assertGreaterEqual(q2.total_matches, 0)

    def test_retrieval_ordering_deterministic(self):
        records = self._records()
        a = retrieve_memory_records(records, 'success')
        b = retrieve_memory_records(records, 'success')
        self.assertEqual(
            [r.memory_id for r in a.matched_records],
            [r.memory_id for r in b.matched_records],
        )

    def test_timeline_summary_aggregation(self):
        records = self._records()
        tl = build_memory_timeline(records)
        s = summarize_memory_timeline(tl)
        self.assertEqual(s['total_records'], tl.total_records)

    def test_corpus_and_exports(self):
        records = self._records()
        tl = build_memory_timeline(records)
        corpus = build_memory_corpus(records)

        out = Path('/workspace/tmp/control-plane-memory')
        out.mkdir(parents=True, exist_ok=True)
        self.assertTrue(Path(export_memory_timeline_json(tl, out / 'timeline.json')).exists())
        self.assertTrue(Path(export_memory_timeline_markdown(tl, out / 'timeline.md')).exists())
        self.assertTrue(Path(export_memory_corpus_json(corpus, out / 'corpus.json')).exists())

    def test_missing_fields_safe(self):
        records = self._records()
        records[0].task = None
        res = retrieve_memory_records(records, 'list')
        self.assertGreaterEqual(res.total_matches, 0)

    def test_cli_commands(self):
        p1 = subprocess.run(['/workspace/ai-orchestrate', 'memory-timeline', '/workspace/runs'], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('timeline_id', j1)

        p2 = subprocess.run(['/workspace/ai-orchestrate', 'retrieve-memory', '/workspace/runs', 'list'], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIn('retrieval_id', j2)


if __name__ == '__main__':
    unittest.main()
