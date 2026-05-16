#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from runtime import adapter_gateway


class AdapterGatewayTests(unittest.TestCase):

    def test_parse_adapter_output_valid(self) -> None:
        payload = adapter_gateway.parse_adapter_output('{"status":"done","output":"ok","meta":{"run_id":"r"}}')
        self.assertEqual(payload['status'], 'done')

    def test_parse_adapter_output_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Invalid runtime JSON'):
            adapter_gateway.parse_adapter_output('not-json')

    def test_validate_adapter_response_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Invalid adapter contract'):
            adapter_gateway.validate_adapter_response({'status': 'done'})

    def test_validate_adapter_response_valid(self) -> None:
        payload = {
            'schema_version': 1,
            'status': 'done',
            'output': 'ok',
            'meta': {'run_id': 'r', 'run_path': '/workspace/runs/run_x', 'error': False},
        }
        out = adapter_gateway.validate_adapter_response(payload)
        self.assertEqual(out['status'], 'done')
        self.assertEqual(out['meta']['run_id'], 'r')

    def test_execute_adapter_command_timeout(self) -> None:
        with mock.patch('runtime.adapter_gateway.subprocess.run', side_effect=subprocess.TimeoutExpired('x', timeout=1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                adapter_gateway.execute_adapter_command(['x'], timeout=1)

    def test_invoke_adapter_success_flow(self) -> None:
        payload = {
            'schema_version': 1,
            'status': 'done',
            'output': 'ok',
            'meta': {'run_id': 'r', 'run_path': '/workspace/runs/run_x', 'error': False},
        }
        proc = subprocess.CompletedProcess(args=['x'], returncode=0, stdout=json.dumps(payload), stderr='')
        with mock.patch('runtime.adapter_gateway.execute_adapter_command', return_value=proc) as m_exec:
            out = adapter_gateway.invoke_adapter(['x'])
        self.assertEqual(out['status'], 'done')
        m_exec.assert_called_once()

    def test_invoke_adapter_invalid_json(self) -> None:
        proc = subprocess.CompletedProcess(args=['x'], returncode=0, stdout='bad', stderr='')
        with mock.patch('runtime.adapter_gateway.execute_adapter_command', return_value=proc):
            with self.assertRaisesRegex(ValueError, 'Invalid runtime JSON'):
                adapter_gateway.invoke_adapter(['x'])


if __name__ == '__main__':
    unittest.main(verbosity=2)