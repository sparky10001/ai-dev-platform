#!/usr/bin/env python3
###################################################################
# log_manager.py — Trace & run cleanup (v1.3 PRODUCTION)
###################################################################

import os
import time
import argparse
import tempfile
import shutil
from collections import deque

# ================================================================
# 📁 CONFIG
# ================================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

TRACE_DIR = os.getenv(
    "AI_TRACE_DIR",
    os.path.join(BASE_DIR, "logs", "traces")
)

RUNS_DIR = os.getenv(
    "AI_RUNS_DIR",
    os.path.join(BASE_DIR, "runs")
)

MAX_FILES = int(os.getenv("AI_LOG_MAX_FILES", "50"))
MAX_FILE_SIZE = int(os.getenv("AI_LOG_MAX_SIZE_MB", "5")) * 1024 * 1024
TRUNCATE_LINES = int(os.getenv("AI_LOG_TRUNCATE_LINES", "500"))
MIN_AGE_SEC = int(os.getenv("AI_LOG_MIN_AGE_SEC", "300"))

MAX_RUN_DIRS = int(os.getenv("AI_MAX_RUN_DIRS", "50"))
RUN_RETENTION_SEC = int(os.getenv("AI_RUN_RETENTION_SEC", "86400"))

VERBOSE = os.getenv("AI_LOG_VERBOSE", "0") == "1"
DRY_RUN = os.getenv("AI_LOG_DRY_RUN", "0") == "1"

os.makedirs(TRACE_DIR, exist_ok=True)
os.makedirs(RUNS_DIR, exist_ok=True)

# ================================================================
# ⚙️ CLI
# ================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--protect", help="Trace file to protect")
    return p.parse_args()

def log(msg):
    if VERBOSE:
        print(msg)

# ================================================================
# 🔐 SAFETY
# ================================================================

def is_safe_path(base, target):
    base = os.path.realpath(base)
    target = os.path.realpath(target)
    return target.startswith(base + os.sep)

# ================================================================
# 📂 FILE HELPERS
# ================================================================

def get_trace_files():
    if not os.path.exists(TRACE_DIR):
        return []
    return [
        f for f in os.listdir(TRACE_DIR)
        if f.startswith("ai_trace.") and f.endswith(".log")
    ]

def get_run_dirs():
    if not os.path.exists(RUNS_DIR):
        return []
    return [
        d for d in os.listdir(RUNS_DIR)
        if os.path.isdir(os.path.join(RUNS_DIR, d))
    ]

def trace_path(f):
    return os.path.join(TRACE_DIR, f)

def run_path(d):
    return os.path.join(RUNS_DIR, d)

def sort_by_mtime(paths, base_path_fn):
    def safe_mtime(name):
        try:
            return os.path.getmtime(base_path_fn(name))
        except:
            return 0
    return sorted(paths, key=safe_mtime, reverse=True)

# ================================================================
# ✂️ TRUNCATION
# ================================================================

def truncate_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            tail = deque(f, maxlen=TRUNCATE_LINES)

        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.writelines(tail)
            tmp_path = tmp.name

        if DRY_RUN:
            log(f"[DRY RUN] Would truncate: {os.path.basename(path)}")
        else:
            shutil.move(tmp_path, path)
            log(f"✂️ Truncated: {os.path.basename(path)}")

    except Exception as e:
        print(f"⚠️ Failed to truncate {path}: {e}")

# ================================================================
# 🧹 TRACE CLEANUP
# ================================================================

def cleanup_traces(protected_name=None):
    files = get_trace_files()
    if not files:
        log("No trace files found")
        return

    files = sort_by_mtime(files, trace_path)

    active_file = files[0]
    if protected_name and protected_name in files:
        active_file = protected_name
    elif protected_name:
        log(f"⚠️ Protected file not found: {protected_name}")

    # 🗑️ Remove excess files
    if len(files) > MAX_FILES:
        for f in files[MAX_FILES:]:
            if f == active_file:
                continue

            path = trace_path(f)

            if not is_safe_path(TRACE_DIR, path):
                continue

            try:
                if DRY_RUN:
                    log(f"[DRY RUN] Would remove: {f}")
                else:
                    os.remove(path)
                    log(f"🗑️ Removed: {f}")
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"⚠️ Failed to remove {f}: {e}")

    # ✂️ Truncate large files
    now = time.time()

    for f in files:
        if f == active_file:
            continue

        path = trace_path(f)

        if not os.path.isfile(path):
            continue

        try:
            mtime = os.path.getmtime(path)

            if now - mtime < MIN_AGE_SEC:
                continue

            size = os.path.getsize(path)

            if size > MAX_FILE_SIZE:
                truncate_file(path)

        except Exception as e:
            print(f"⚠️ Failed processing {f}: {e}")

# ================================================================
# 🧹 RUN CLEANUP
# ================================================================

def cleanup_empty_file_dirs(runs):
    for d in runs:
        files_dir = os.path.join(run_path(d), "files")

        if os.path.isdir(files_dir) and not os.listdir(files_dir):
            try:
                if DRY_RUN:
                    log(f"[DRY RUN] Would remove empty dir: {d}/files")
                else:
                    os.rmdir(files_dir)
                    log(f"🧹 Removed empty files dir: {d}")
            except Exception as e:
                print(f"⚠️ Failed removing empty dir {d}: {e}")

def cleanup_runs():
    runs = get_run_dirs()
    if not runs:
        return

    runs = sort_by_mtime(runs, run_path)
    now = time.time()

    # 🧹 Remove expired first
    filtered = []

    for d in runs:
        path = run_path(d)

        try:
            mtime = os.path.getmtime(path)

            if now - mtime > RUN_RETENTION_SEC:
                if not is_safe_path(RUNS_DIR, path):
                    continue

                if DRY_RUN:
                    log(f"[DRY RUN] Would remove expired run: {d}")
                else:
                    shutil.rmtree(path)
                    print(f"🗑️ Expired run removed: {d}")
            else:
                filtered.append(d)

        except Exception as e:
            print(f"⚠️ Failed processing run {d}: {e}")

    runs = sort_by_mtime(filtered, run_path)

    # 🗑️ Enforce max count
    if len(runs) > MAX_RUN_DIRS:
        for d in runs[MAX_RUN_DIRS:]:
            path = run_path(d)

            if not is_safe_path(RUNS_DIR, path):
                continue

            try:
                if DRY_RUN:
                    log(f"[DRY RUN] Would remove run dir: {d}")
                else:
                    shutil.rmtree(path)
                    log(f"🗑️ Removed run dir: {d}")
            except Exception as e:
                print(f"⚠️ Failed removing run dir {d}: {e}")

    # 🧹 Cleanup empty dirs last
    cleanup_empty_file_dirs(runs)

# ================================================================
# 🏁 ENTRYPOINT
# ================================================================

def main():
    args = parse_args()
    protected = os.path.basename(args.protect) if args.protect else None

    try:
        cleanup_traces(protected)
    except Exception as e:
        print(f"⚠️ Trace cleanup failed: {e}")

    try:
        cleanup_runs()
    except Exception as e:
        print(f"⚠️ Run cleanup failed: {e}")

if __name__ == "__main__":
    main()