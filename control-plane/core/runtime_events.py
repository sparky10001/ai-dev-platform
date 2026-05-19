#!/usr/bin/env python3
"""
Control-plane runtime event compatibility bridge.

This module provides read-side access to canonical runtime events
without coupling control-plane systems to trace-file assumptions
or runtime execution modules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Iterator

from runtime.event_loader import iter_runtime_events
from runtime.event_loader import load_runtime_events
from runtime.event_loader import resolve_runtime_event_source


def control_plane_runtime_event_source(source: str | None = None, default: str = "trace") -> str:
    return resolve_runtime_event_source(source=source, default=default)


def _event_to_dict(event: Any) -> dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    return dict(event)


def _normalize_events(events: Iterable[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        payload = _event_to_dict(event)
        if isinstance(payload, dict):
            normalized.append(payload)
    return normalized


def iter_control_plane_runtime_events(
    run_or_path: str | Path,
    source: str | None = None,
    strict: bool = False,
) -> Iterator[dict[str, Any]]:
    resolved_source = control_plane_runtime_event_source(source=source, default="trace")
    for event in iter_runtime_events(run_or_path, source=resolved_source, strict=strict):
        payload = _event_to_dict(event)
        if isinstance(payload, dict):
            yield payload


def load_control_plane_runtime_events(
    run_or_path: str | Path,
    source: str | None = None,
    strict: bool = False,
) -> list[dict[str, Any]]:
    resolved_source = control_plane_runtime_event_source(source=source, default="trace")
    events = load_runtime_events(run_or_path, source=resolved_source, strict=strict)
    return _normalize_events(events)
