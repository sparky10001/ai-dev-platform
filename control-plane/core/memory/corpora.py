#!/usr/bin/env python3
from __future__ import annotations

import time

from core.memory.models import MemoryCorpus
from core.memory.models import MemoryRecord


def build_memory_corpus(
    records: list[MemoryRecord],
    corpus_id: str = 'memory-corpus',
) -> MemoryCorpus:

    ordered = sorted(records, key=lambda r: ((r.created_at if r.created_at is not None else float('inf')), (r.run_id or '')))

    return MemoryCorpus(
        corpus_id=corpus_id,
        created_at=time.time(),
        total_records=len(ordered),
        records=ordered,
        metadata={},
    )
