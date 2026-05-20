#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any, Literal

RuntimeAuthorityMode = Literal["trace", "canary", "authoritative"]
RuntimeEventSource = Literal["trace", "ledger"]


def ledger_authoritative_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_AUTHORITATIVE") == "1"


def ledger_canary_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_CANARY") == "1"


def ledger_default_dry_run_enabled() -> bool:
    return os.getenv("RUNTIME_LEDGER_DRY_RUN_DEFAULT") == "1"


def runtime_authority_mode() -> RuntimeAuthorityMode:
    if ledger_authoritative_enabled():
        return "authoritative"
    if ledger_canary_enabled():
        return "canary"
    return "trace"


def _normalize_source(value: str | None) -> RuntimeEventSource | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in ("trace", "ledger"):
        return normalized  # type: ignore[return-value]
    return None


def effective_runtime_event_source(source: str | None = None, default: str = "trace") -> RuntimeEventSource:
    normalized_default = _normalize_source(default) or "trace"
    fallback: RuntimeEventSource = "ledger" if runtime_authority_mode() in {"canary", "authoritative"} else normalized_default

    explicit = _normalize_source(source)
    if explicit is not None:
        return explicit
    if source is not None:
        return fallback

    env_source = _normalize_source(os.getenv("RUNTIME_EVENT_SOURCE"))
    if env_source is not None:
        return env_source

    return fallback


def runtime_authority_transition_state() -> dict[str, Any]:
    mode = runtime_authority_mode()
    canary = ledger_canary_enabled()
    authoritative = ledger_authoritative_enabled()
    dry_run = ledger_default_dry_run_enabled()
    rollback_unset = [
        "RUNTIME_LEDGER_CANARY",
        "RUNTIME_LEDGER_AUTHORITATIVE",
        "RUNTIME_LEDGER_PARITY_REQUIRED",
        "RUNTIME_LEDGER_CANARY_PARITY_REQUIRED",
    ]
    return {
        "current_default": "trace",
        "effective_mode": mode,
        "canary_enabled": canary,
        "authoritative_enabled": authoritative,
        "dry_run_enabled": dry_run,
        "default_cutover_performed": False,
        "trace_emission_enabled": True,
        "rollback_supported": True,
        "rollback_method": "env_unset",
        "rollback_unset": rollback_unset,
    }


def runtime_authority_policy() -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    return {
        "mode": transition["effective_mode"],
        "event_source": effective_runtime_event_source(),
        "flags": {
            "canary_enabled": transition["canary_enabled"],
            "authoritative_enabled": transition["authoritative_enabled"],
            "dry_run_enabled": transition["dry_run_enabled"],
        },
        "transition": transition,
    }
