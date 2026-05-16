#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest import mock

from runtime import run_lifecycle


class RunLifecycleTests(unittest.TestCase):

    def test_build_response_error_shape(self) -> None:
        out = run_lifecycle.build_response('boom', run_id='r1', run_path='/workspace/runs/r1')
        dumped = out.model_dump(mode='json')
        self.assertEqual(dumped['status'], 'error')
        self.assertEqual(dumped['meta']['run_id'], 'r1')
        self.assertEqual(dumped['meta']['run_path'], '/workspace/runs/r1')
        self.assertTrue(dumped['meta']['error'])

    def test_initialize_run_delegates(self) -> None:
        with mock.patch('runtime.run_lifecycle.create_run', return_value={'id': 'r'}) as m:
            out = run_lifecycle.initialize_run('t', 'run', 'heavy')
        self.assertEqual(out['id'], 'r')
        m.assert_called_once_with(task='t', command='run', model='heavy')

    def test_start_run_logs_session_start(self) -> None:
        run = {'id': 'r', 'trace_path': '/tmp/t'}
        with mock.patch('runtime.run_lifecycle.log_event') as m:
            run_lifecycle.start_run(run, 'run', 'hello', 'heavy')
        m.assert_called_once()
        self.assertEqual(m.call_args.args[1], 'session_start')

    def test_record_agent_output_logs(self) -> None:
        run = {'id': 'r', 'trace_path': '/tmp/t'}
        with mock.patch('runtime.run_lifecycle.log_event') as m:
            run_lifecycle.record_agent_output(run, 'done', 'ok')
        self.assertEqual(m.call_args.args[1], 'agent_output')

    def test_finalize_run_orders_end_then_persist(self) -> None:
        run = {'id': 'r', 'trace_path': '/tmp/t'}
        result = {'status': 'done'}
        with mock.patch('runtime.run_lifecycle.log_event') as m_event, mock.patch('runtime.run_lifecycle.finalize_run_record') as m_fin:
            run_lifecycle.finalize_run(run, 'done', result)
        self.assertEqual(m_event.call_args.args[1], 'session_end')
        m_fin.assert_called_once_with(run, result)

    def test_fail_run_returns_error_response(self) -> None:
        run = {'id': 'r', 'run_path': '/workspace/runs/r', 'trace_path': '/tmp/t'}
        with mock.patch('runtime.run_lifecycle.record_agent_output'), mock.patch('runtime.run_lifecycle.log_event'), mock.patch('runtime.run_lifecycle.finalize_run_record'):
            res = run_lifecycle.fail_run(run, 'bad')
        dumped = res.model_dump(mode='json')
        self.assertEqual(dumped['status'], 'error')
        self.assertEqual(dumped['output'], 'bad')


if __name__ == '__main__':
    unittest.main(verbosity=2)