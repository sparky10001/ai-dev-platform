#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from runtime.trace_pipeline import append_trace_event


def log_event(
    run: dict,
    event: str,
    data: Any = None,
    **extra
):

    append_trace_event(
        run=run,
        event=event,
        data=data,
        **extra,
    )
