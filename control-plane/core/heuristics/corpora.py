#!/usr/bin/env python3
from __future__ import annotations

import time

from core.heuristics.models import HeuristicCorpus
from core.heuristics.models import HeuristicSignal


def build_heuristic_corpus(
    signals: list[HeuristicSignal],
    corpus_id: str = 'corpus',
) -> HeuristicCorpus:

    ordered = sorted(signals, key=lambda s: s.signal_id)

    return HeuristicCorpus(
        corpus_id=corpus_id,
        created_at=time.time(),
        total_signals=len(ordered),
        signals=ordered,
        metadata={},
    )
