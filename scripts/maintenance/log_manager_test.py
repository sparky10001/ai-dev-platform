#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path


class LogManagerTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='log_manager_test_'))
        self.trace_dir = self.tmp / 'logs' / 'traces'
        self.runs_dir = self.tmp / 'runs'
        self.lock_file = self.tmp / 'tmp' / 'log_manager.lock'
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self.mod = importlib.import_module('scripts.maintenance.log_manager')

        ns = type('Args', (), {
            'protect': None,
            'dry_run': False,
            'verbose': False,
            'trace_dir': str(self.trace_dir),
            'runs_dir': str(self.runs_dir),
        })
        os.environ['AI_LOG_LOCK_FILE'] = str(self.lock_file)
        self.cfg = self.mod.build_config(ns)

    def tearDown(self) -> None:
        os.environ.pop('AI_TRACE_DIR', None)
        os.environ.pop('AI_RUNS_DIR', None)
        os.environ.pop('AI_LOG_LOCK_FILE', None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _trace(self, name: str, content: str = 'x\n') -> Path:
        p = self.trace_dir / name
        p.write_text(content, encoding='utf-8')
        return p

    def _set_mtime(self, path: Path, age_sec: int) -> None:
        ts = time.time() - age_sec
        os.utime(path, (ts, ts))

    def test_dry_run_deletes_nothing(self):
        a = self._trace('ai_trace.1.log')
        b = self._trace('ai_trace.2.log')
        self._set_mtime(a, 100)
        self._set_mtime(b, 200)
        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'max_files': 1, 'dry_run': True, 'verbose': True})

        self.mod.cleanup_traces(cfg)
        self.assertTrue(a.exists())
        self.assertTrue(b.exists())

    def test_protected_trace_not_removed(self):
        files = []
        for i in range(4):
            p = self._trace(f'ai_trace.{i}.log')
            self._set_mtime(p, 1000 + i)
            files.append(p)

        protected = files[-1].name
        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'max_files': 1})
        self.mod.cleanup_traces(cfg, protected)
        self.assertTrue((self.trace_dir / protected).exists())

    def test_oldest_excess_trace_files_removed(self):
        for i in range(4):
            p = self._trace(f'ai_trace.{i}.log')
            self._set_mtime(p, 100 + i)
        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'max_files': 2})

        self.mod.cleanup_traces(cfg)
        remaining = sorted(x.name for x in self.trace_dir.glob('ai_trace.*.log'))
        self.assertEqual(len(remaining), 2)

    def test_large_old_trace_truncates_to_tail_lines(self):
        p = self._trace('ai_trace.big.log', ''.join(f'line-{i}\n' for i in range(1000)))
        self._set_mtime(p, 5000)
        active = self._trace('ai_trace.active.log', 'active\n')
        self._set_mtime(active, 1)

        cfg = self.cfg.__class__(**{
            **self.cfg.__dict__,
            'max_file_size': 128,
            'truncate_lines': 10,
            'min_age_sec': 300,
        })
        self.mod.cleanup_traces(cfg)

        lines = p.read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 10)
        self.assertEqual(lines[0], 'line-990')

    def test_recent_large_trace_not_truncated(self):
        p = self._trace('ai_trace.recent.log', ''.join(f'line-{i}\n' for i in range(400)))
        self._set_mtime(p, 1)
        old_size = p.stat().st_size
        cfg = self.cfg.__class__(**{
            **self.cfg.__dict__,
            'max_file_size': 128,
            'min_age_sec': 300,
            'truncate_lines': 5,
        })

        self.mod.cleanup_traces(cfg)
        self.assertEqual(p.stat().st_size, old_size)

    def test_expired_run_dirs_removed(self):
        old = self.runs_dir / 'run_old'
        new = self.runs_dir / 'run_new'
        old.mkdir()
        new.mkdir()
        self._set_mtime(old, 10000)
        self._set_mtime(new, 1)

        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'run_retention_sec': 100})
        self.mod.cleanup_runs(cfg)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())

    def test_max_run_dirs_enforced(self):
        for i in range(5):
            d = self.runs_dir / f'run_{i}'
            d.mkdir()
            self._set_mtime(d, i + 10)

        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'max_run_dirs': 2, 'run_retention_sec': 999999})
        self.mod.cleanup_runs(cfg)
        remain = [d for d in self.runs_dir.iterdir() if d.is_dir()]
        self.assertLessEqual(len(remain), 2)

    def test_empty_files_dirs_removed(self):
        run = self.runs_dir / 'run_1'
        files = run / 'files'
        files.mkdir(parents=True)
        cfg = self.cfg.__class__(**self.cfg.__dict__)

        self.mod.cleanup_empty_file_dirs(cfg, ['run_1'])
        self.assertFalse(files.exists())

    def test_unsafe_symlink_escape_not_removed(self):
        outside = self.tmp / 'outside'
        outside.mkdir()
        target = outside / 'run_bad'
        target.mkdir()
        symlink = self.runs_dir / 'run_symlink'
        symlink.symlink_to(target, target_is_directory=True)

        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'run_retention_sec': 1})
        self.mod.cleanup_runs(cfg)
        self.assertTrue(target.exists())

    def test_import_does_not_create_directories(self):
        alt = Path(tempfile.mkdtemp(prefix='log_manager_import_'))
        try:
            trace_dir = alt / 'not_created_trace'
            runs_dir = alt / 'not_created_runs'
            os.environ['AI_TRACE_DIR'] = str(trace_dir)
            os.environ['AI_RUNS_DIR'] = str(runs_dir)
            mod = importlib.reload(self.mod)
            self.assertFalse(trace_dir.exists())
            self.assertFalse(runs_dir.exists())
            _ = mod
        finally:
            os.environ.pop('AI_TRACE_DIR', None)
            os.environ.pop('AI_RUNS_DIR', None)
            shutil.rmtree(alt, ignore_errors=True)

    def test_lock_acquisition(self):
        h = self.mod.acquire_lock(self.cfg)
        self.assertIsNotNone(h)
        if h is not None:
            self.mod.release_lock(h)

    def test_second_nonblocking_acquisition_returns_none(self):
        h1 = self.mod.acquire_lock(self.cfg)
        self.assertIsNotNone(h1)
        try:
            h2 = self.mod.acquire_lock(self.cfg)
            self.assertIsNone(h2)
        finally:
            if h1 is not None:
                self.mod.release_lock(h1)

    def test_custom_lock_file_path(self):
        custom_lock = self.tmp / 'custom' / 'maintenance.lock'
        cfg = self.cfg.__class__(**{**self.cfg.__dict__, 'lock_file': custom_lock})
        h = self.mod.acquire_lock(cfg)
        self.assertIsNotNone(h)
        self.assertTrue(custom_lock.exists())
        if h is not None:
            self.mod.release_lock(h)


if __name__ == '__main__':
    unittest.main()
