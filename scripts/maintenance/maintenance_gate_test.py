#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from scripts.maintenance.maintenance_gate import mark_maintenance_run
from scripts.maintenance.maintenance_gate import maybe_run_maintenance
from scripts.maintenance.maintenance_gate import should_run_maintenance


class MaintenanceGateTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='maintenance_gate_test_'))
        self.stamp = self.tmp / '.stamp'

    def tearDown(self) -> None:
        os.environ.pop('AI_MAINTENANCE_ENABLED', None)
        os.environ.pop('AI_MAINTENANCE_INTERVAL_SEC', None)
        os.environ.pop('AI_MAINTENANCE_TIMEOUT_SEC', None)
        os.environ.pop('AI_MAINTENANCE_STAMP_PATH', None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_disabled_by_default_skips(self):
        res = maybe_run_maintenance(command=['python3', '-c', 'print("ok")'], stamp_path=self.stamp)
        self.assertEqual(res['status'], 'skipped')
        self.assertEqual(res['reason'], 'disabled')

    def test_enabled_and_no_stamp_runs_command(self):
        res = maybe_run_maintenance(
            command=['python3', '-c', 'print("ok")'],
            stamp_path=self.stamp,
            enabled=True,
            interval_sec=300,
        )
        self.assertEqual(res['status'], 'success')
        self.assertTrue(self.stamp.exists())

    def test_enabled_and_recent_stamp_skips(self):
        mark_maintenance_run(now=time.time(), stamp_path=self.stamp)
        res = maybe_run_maintenance(
            command=['python3', '-c', 'print("ok")'],
            stamp_path=self.stamp,
            enabled=True,
            interval_sec=300,
        )
        self.assertEqual(res['status'], 'skipped')
        self.assertEqual(res['reason'], 'interval_not_elapsed')

    def test_mark_maintenance_run_writes_stamp(self):
        mark_maintenance_run(now=1234.5, stamp_path=self.stamp)
        self.assertTrue(self.stamp.exists())
        self.assertEqual(float(self.stamp.read_text(encoding='utf-8').strip()), 1234.5)

    def test_invalid_interval_handled_deterministically(self):
        os.environ['AI_MAINTENANCE_INTERVAL_SEC'] = 'not-an-int'
        self.assertTrue(should_run_maintenance(stamp_path=self.stamp))

    def test_command_failure_returns_error_no_raise(self):
        res = maybe_run_maintenance(
            command=['python3', '-c', 'import sys; sys.exit(7)'],
            stamp_path=self.stamp,
            enabled=True,
            interval_sec=0,
        )
        self.assertEqual(res['status'], 'error')
        self.assertEqual(res['reason'], 'command_failed')
        self.assertEqual(res['returncode'], 7)

    def test_timeout_returns_error_result(self):
        os.environ['AI_MAINTENANCE_TIMEOUT_SEC'] = '1'
        res = maybe_run_maintenance(
            command=['python3', '-c', 'import time; time.sleep(2)'],
            stamp_path=self.stamp,
            enabled=True,
            interval_sec=0,
        )
        self.assertEqual(res['status'], 'error')
        self.assertEqual(res['reason'], 'timeout')

    def test_custom_stamp_path_works(self):
        custom = self.tmp / 'custom' / '.last'
        res = maybe_run_maintenance(
            command=['python3', '-c', 'print("ok")'],
            stamp_path=custom,
            enabled=True,
            interval_sec=0,
        )
        self.assertEqual(res['status'], 'success')
        self.assertTrue(custom.exists())


if __name__ == '__main__':
    unittest.main()
