#!/usr/bin/env python3
###################################################################
# maintenance_gate.py — Optional throttled maintenance trigger
###################################################################

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STAMP = BASE_DIR / "tmp" / ".last_log_maintenance"
DEFAULT_COMMAND = ["python3", "scripts/maintenance/log_manager.py"]


def _as_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < 0:
        return default
    return value


def _stamp_path(stamp_path: str | Path | None) -> Path:
    if stamp_path is None:
        return Path(os.getenv("AI_MAINTENANCE_STAMP_PATH") or DEFAULT_STAMP)
    return Path(stamp_path)


def should_run_maintenance(now: float | None = None, interval_sec: int | None = None, stamp_path: str | Path | None = None) -> bool:
    ts = time.time() if now is None else float(now)
    interval = interval_sec if interval_sec is not None else _as_int(os.getenv("AI_MAINTENANCE_INTERVAL_SEC"), 300)
    if interval <= 0:
        interval = 300

    stamp = _stamp_path(stamp_path)
    if not stamp.exists():
        return True

    try:
        last = float(stamp.read_text(encoding="utf-8").strip())
    except Exception:
        return True

    return (ts - last) >= interval


def mark_maintenance_run(now: float | None = None, stamp_path: str | Path | None = None) -> None:
    ts = time.time() if now is None else float(now)
    stamp = _stamp_path(stamp_path)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(str(ts), encoding="utf-8")


def maybe_run_maintenance(
    command: list[str] | None = None,
    interval_sec: int | None = None,
    stamp_path: str | Path | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    is_enabled = enabled if enabled is not None else os.getenv("AI_MAINTENANCE_ENABLED", "0") == "1"
    if not is_enabled:
        return {
            "status": "skipped",
            "reason": "disabled",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        }

    interval = interval_sec if interval_sec is not None else _as_int(os.getenv("AI_MAINTENANCE_INTERVAL_SEC"), 300)
    if interval <= 0:
        interval = 300

    if not should_run_maintenance(interval_sec=interval, stamp_path=stamp_path):
        return {
            "status": "skipped",
            "reason": "interval_not_elapsed",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        }

    timeout_sec = _as_int(os.getenv("AI_MAINTENANCE_TIMEOUT_SEC"), 30)
    if timeout_sec <= 0:
        timeout_sec = 30

    cmd = command or DEFAULT_COMMAND

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "error",
            "reason": "timeout",
            "returncode": -1,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except Exception as exc:
        return {
            "status": "error",
            "reason": "exception",
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
        }

    if proc.returncode == 0:
        mark_maintenance_run(stamp_path=stamp_path)
        return {
            "status": "success",
            "reason": "executed",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    return {
        "status": "error",
        "reason": "command_failed",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
