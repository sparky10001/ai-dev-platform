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

from core.heuristics.corpora import build_heuristic_corpus
from core.heuristics.exporter import export_corpus_markdown
from core.heuristics.exporter import export_ranking_json
from core.heuristics.exporter import export_recommendation_json
from core.heuristics.ranking import generate_heuristic_signals
from core.heuristics.ranking import rank_strategy_variants
from core.heuristics.recommender import recommend_strategy
from core.strategies.branching import execute_strategy_experiment


class AdaptiveHeuristicTests(unittest.TestCase):

    def _experiment(self):
        return execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default', 'safe-readonly'],
            trace=True,
        )

    def test_signal_generation_and_order(self):
        exp = self._experiment()
        signals = generate_heuristic_signals(exp.variants)
        ids = [s.signal_id for s in signals]
        self.assertEqual(ids, sorted(ids))

    def test_ranking_and_tie_break(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic', 'noop'],
            policies=['default'],
            trace=False,
        )
        ranking = rank_strategy_variants(exp.variants, ranking_id='r1')
        self.assertEqual(ranking.ranked_strategy_ids, sorted(ranking.ranked_strategy_ids))

    def test_ranking_average(self):
        exp = self._experiment()
        ranking = rank_strategy_variants(exp.variants)
        self.assertGreaterEqual(ranking.average_score, 0.0)

    def test_recommendation_generation(self):
        exp = self._experiment()
        signals = generate_heuristic_signals(exp.variants)
        rec = recommend_strategy('list files', signals)
        self.assertTrue(rec.recommendation_id)
        self.assertGreaterEqual(rec.confidence, 0.0)
        self.assertLessEqual(rec.confidence, 1.0)

    def test_recommendation_deterministic(self):
        exp = self._experiment()
        signals = generate_heuristic_signals(exp.variants)
        a = recommend_strategy('list files', signals)
        b = recommend_strategy('list files', signals)
        self.assertEqual(a.model_dump(mode='json'), b.model_dump(mode='json'))

    def test_corpus_and_counts(self):
        exp = self._experiment()
        signals = generate_heuristic_signals(exp.variants)
        corpus = build_heuristic_corpus(signals, corpus_id='c1')
        self.assertEqual(corpus.total_signals, len(signals))

    def test_exports(self):
        exp = self._experiment()
        signals = generate_heuristic_signals(exp.variants)
        ranking = rank_strategy_variants(exp.variants)
        rec = recommend_strategy('list files', signals)
        corpus = build_heuristic_corpus(signals)

        out = Path('/workspace/tmp/control-plane-heuristics')
        out.mkdir(parents=True, exist_ok=True)
        self.assertTrue(Path(export_ranking_json(ranking, out / 'ranking.json')).exists())
        self.assertTrue(Path(export_recommendation_json(rec, out / 'rec.json')).exists())
        self.assertTrue(Path(export_corpus_markdown(corpus, out / 'corpus.md')).exists())

    def test_missing_policy_and_missing_scores_safe(self):
        exp = execute_strategy_experiment(
            task='list files',
            planner_strategies=['deterministic'],
            policies=None,
            trace=False,
        )
        signals = generate_heuristic_signals(exp.variants)
        rec = recommend_strategy('list files', signals)
        self.assertIsNotNone(rec.recommended_planner)

    def test_cli_commands(self):
        p1 = subprocess.run([
            '/workspace/ai-orchestrate', 'recommend-strategy', 'list files'
        ], capture_output=True, text=True)
        self.assertEqual(p1.returncode, 0)
        j1 = json.loads(p1.stdout)
        self.assertIn('recommendation_id', j1)

        p2 = subprocess.run([
            '/workspace/ai-orchestrate', 'rank-strategies', 'list files', '--planner=deterministic', '--planner=noop'
        ], capture_output=True, text=True)
        self.assertEqual(p2.returncode, 0)
        j2 = json.loads(p2.stdout)
        self.assertIn('ranking_id', j2)


if __name__ == '__main__':
    unittest.main()
