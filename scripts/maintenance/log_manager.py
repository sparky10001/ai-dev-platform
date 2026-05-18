#!/usr/bin/env python3
###################################################################
# log_manager.py — Trace & run cleanup (v1.5 maintenance-integrated)
###################################################################

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LogManagerConfig:
    trace_dir: Path
    runs_dir: Path
    lock_file: Path
    max_files: int
    max_file_size: int
    truncate_lines: int
    min_age_sec: int
    max_run_dirs: int
    run_retention_sec: int
    verbose: bool
    dry_run: bool


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--protect", help="Trace file to protect")
    p.add_argument("--dry-run", action="store_true", help="Do not modify filesystem")
    p.add_argument("--verbose", action="store_true", help="Enable verbose logs")
    p.add_argument("--trace-dir", help="Override trace directory")
    p.add_argument("--runs-dir", help="Override runs directory")
    return p.parse_args()


def build_config(args: argparse.Namespace) -> LogManagerConfig:
    trace_dir = Path(
        args.trace_dir
        or os.getenv("AI_TRACE_DIR")
        or str(BASE_DIR / "logs" / "traces")
    )
    runs_dir = Path(
        args.runs_dir
        or os.getenv("AI_RUNS_DIR")
        or str(BASE_DIR / "runs")
    )
    lock_file = Path(
        os.getenv("AI_LOG_LOCK_FILE")
        or str(BASE_DIR / "tmp" / "log_manager.lock")
    )

    verbose = args.verbose or os.getenv("AI_LOG_VERBOSE", "0") == "1"
    dry_run = args.dry_run or os.getenv("AI_LOG_DRY_RUN", "0") == "1"

    return LogManagerConfig(
        trace_dir=trace_dir,
        runs_dir=runs_dir,
        lock_file=lock_file,
        max_files=int(os.getenv("AI_LOG_MAX_FILES", "50")),
        max_file_size=int(os.getenv("AI_LOG_MAX_SIZE_MB", "5")) * 1024 * 1024,
        truncate_lines=int(os.getenv("AI_LOG_TRUNCATE_LINES", "500")),
        min_age_sec=int(os.getenv("AI_LOG_MIN_AGE_SEC", "300")),
        max_run_dirs=int(os.getenv("AI_MAX_RUN_DIRS", "50")),
        run_retention_sec=int(os.getenv("AI_RUN_RETENTION_SEC", "86400")),
        verbose=verbose,
        dry_run=dry_run,
    )


def ensure_dirs(cfg: LogManagerConfig) -> None:
    cfg.trace_dir.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.lock_file.parent.mkdir(parents=True, exist_ok=True)


def log(cfg: LogManagerConfig, msg: str) -> None:
    if cfg.verbose:
        print(msg)


def is_safe_path(base: Path | str, target: Path | str, *, allow_equal: bool = False) -> bool:
    try:
        base_path = Path(base).resolve(strict=False)
        target_path = Path(target).resolve(strict=False)
    except Exception:
        return False

    if target_path == base_path:
        return allow_equal

    try:
        target_path.relative_to(base_path)
    except ValueError:
        return False

    return True


def acquire_lock(cfg: LogManagerConfig) -> TextIO | None:
    cfg.lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle = cfg.lock_file.open("a+", encoding="utf-8")

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None

    return handle


def release_lock(handle: TextIO) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        handle.close()


def get_trace_files(cfg: LogManagerConfig) -> list[str]:
    if not cfg.trace_dir.exists():
        return []

    return [
        f.name for f in cfg.trace_dir.iterdir()
        if f.is_file() and f.name.startswith("ai_trace.") and f.name.endswith(".log")
    ]


def get_run_dirs(cfg: LogManagerConfig) -> list[str]:
    if not cfg.runs_dir.exists():
        return []

    return [d.name for d in cfg.runs_dir.iterdir() if d.is_dir()]


def trace_path(cfg: LogManagerConfig, f: str) -> Path:
    return cfg.trace_dir / f


def run_path(cfg: LogManagerConfig, d: str) -> Path:
    return cfg.runs_dir / d


def sort_by_mtime(paths: list[str], base_path_fn) -> list[str]:
    def safe_mtime(name: str) -> float:
        try:
            return base_path_fn(name).stat().st_mtime
        except Exception:
            return 0

    return sorted(paths, key=safe_mtime, reverse=True)


def truncate_file(cfg: LogManagerConfig, path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            tail = deque(f, maxlen=cfg.truncate_lines)

        if cfg.dry_run:
            log(cfg, f"[DRY RUN] Would truncate: {path.name}")
            return

        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
            tmp.writelines(tail)
            tmp_path = Path(tmp.name)

        shutil.move(str(tmp_path), str(path))
        log(cfg, f"✂️ Truncated: {path.name}")

    except Exception as e:
        print(f"⚠️ Failed to truncate {path}: {e}")


def cleanup_traces(cfg: LogManagerConfig, protected_name: str | None = None) -> None:
    files = get_trace_files(cfg)
    if not files:
        log(cfg, "No trace files found")
        return

    files = sort_by_mtime(files, lambda name: trace_path(cfg, name))

    active_file = files[0]
    if protected_name and protected_name in files:
        active_file = protected_name
    elif protected_name:
        log(cfg, f"⚠️ Protected file not found: {protected_name}")

    if len(files) > cfg.max_files:
        for f in files[cfg.max_files:]:
            if f == active_file:
                continue

            path = trace_path(cfg, f)

            if not is_safe_path(cfg.trace_dir, path):
                continue

            try:
                if cfg.dry_run:
                    log(cfg, f"[DRY RUN] Would remove: {f}")
                else:
                    path.unlink()
                    log(cfg, f"🗑️ Removed: {f}")
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"⚠️ Failed to remove {f}: {e}")

    now = time.time()
    for f in files:
        if f == active_file:
            continue

        path = trace_path(cfg, f)

        if not path.is_file():
            continue

        try:
            mtime = path.stat().st_mtime
            if now - mtime < cfg.min_age_sec:
                continue

            if path.stat().st_size > cfg.max_file_size:
                truncate_file(cfg, path)

        except Exception as e:
            print(f"⚠️ Failed processing {f}: {e}")


def cleanup_empty_file_dirs(cfg: LogManagerConfig, runs: list[str]) -> None:
    for d in runs:
        files_dir = run_path(cfg, d) / "files"

        if files_dir.is_dir() and not any(files_dir.iterdir()):
            if not is_safe_path(cfg.runs_dir, files_dir):
                continue

            try:
                if cfg.dry_run:
                    log(cfg, f"[DRY RUN] Would remove empty dir: {d}/files")
                else:
                    files_dir.rmdir()
                    log(cfg, f"🧹 Removed empty files dir: {d}")
            except Exception as e:
                print(f"⚠️ Failed removing empty dir {d}: {e}")


def cleanup_runs(cfg: LogManagerConfig) -> None:
    runs = get_run_dirs(cfg)
    if not runs:
        return

    runs = sort_by_mtime(runs, lambda name: run_path(cfg, name))
    now = time.time()

    filtered: list[str] = []

    for d in runs:
        path = run_path(cfg, d)

        try:
            mtime = path.stat().st_mtime
            if now - mtime > cfg.run_retention_sec:
                if not is_safe_path(cfg.runs_dir, path):
                    continue

                if cfg.dry_run:
                    log(cfg, f"[DRY RUN] Would remove expired run: {d}")
                else:
                    shutil.rmtree(path)
                    print(f"🗑️ Expired run removed: {d}")
            else:
                filtered.append(d)

        except Exception as e:
            print(f"⚠️ Failed processing run {d}: {e}")

    runs = sort_by_mtime(filtered, lambda name: run_path(cfg, name))

    if len(runs) > cfg.max_run_dirs:
        for d in runs[cfg.max_run_dirs:]:
            path = run_path(cfg, d)

            if not is_safe_path(cfg.runs_dir, path):
                continue

            try:
                if cfg.dry_run:
                    log(cfg, f"[DRY RUN] Would remove run dir: {d}")
                else:
                    shutil.rmtree(path)
                    log(cfg, f"🗑️ Removed run dir: {d}")
            except Exception as e:
                print(f"⚠️ Failed removing run dir {d}: {e}")

    cleanup_empty_file_dirs(cfg, runs)


def run_cleanup(cfg: LogManagerConfig, protected_name: str | None = None) -> int:
    handle = acquire_lock(cfg)
    if handle is None:
        log(cfg, "maintenance already running")
        return 0

    try:
        try:
            cleanup_traces(cfg, protected_name)
        except Exception as e:
            print(f"⚠️ Trace cleanup failed: {e}")

        try:
            cleanup_runs(cfg)
        except Exception as e:
            print(f"⚠️ Run cleanup failed: {e}")

        return 0
    finally:
        release_lock(handle)


def main() -> int:
    args = parse_args()
    cfg = build_config(args)
    protected = Path(args.protect).name if args.protect else None

    ensure_dirs(cfg)
    return run_cleanup(cfg, protected)


if __name__ == "__main__":
    raise SystemExit(main())
