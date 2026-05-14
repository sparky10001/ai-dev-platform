#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path
import sys

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from tools.registry import build_registry
from tools.registry import get_tool
from tools.registry import load_openai_tools
from tools.registry import normalize_openai_tool
from tools.registry import validate_tool_args
from tools.registry import validate_tool_node


class ToolRegistryTests(unittest.TestCase):

    def test_load_openai_tools_non_empty(self):

        tools = load_openai_tools()

        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

    def test_build_registry_has_expected_tools(self):

        snapshot = build_registry()

        self.assertIn('read_file', snapshot.tools)
        self.assertIn('write_file', snapshot.tools)
        self.assertIn('list_files', snapshot.tools)
        self.assertIn('run_bash', snapshot.tools)

    def test_get_tool_write_file(self):

        tool = get_tool('write_file')

        self.assertEqual(tool.name, 'write_file')
        self.assertIn('path', tool.required)
        self.assertIn('content', tool.required)

    def test_validate_tool_args_write_file(self):

        tool = get_tool('write_file')

        self.assertTrue(
            validate_tool_args(
                tool,
                {
                    'path': 'hello.txt',
                    'content': 'hi',
                },
            )
        )

        self.assertFalse(
            validate_tool_args(
                tool,
                {
                    'path': 'hello.txt',
                },
            )
        )

    def test_validate_tool_node_list_files(self):

        self.assertTrue(validate_tool_node('list_files', {}))

    def test_missing_tool_raises(self):

        with self.assertRaises(KeyError):
            get_tool('no_such_tool')

    def test_duplicate_name_rejected(self):

        # Monkeypatch loader inside this module scope.
        import tools.registry as registry

        original = registry.load_openai_tools

        try:
            registry.load_openai_tools = lambda: [
                {
                    'type': 'function',
                    'function': {
                        'name': 'dup',
                        'description': 'one',
                        'parameters': {'type': 'object'},
                    },
                },
                {
                    'type': 'function',
                    'function': {
                        'name': 'dup',
                        'description': 'two',
                        'parameters': {'type': 'object'},
                    },
                },
            ]

            with self.assertRaises(ValueError):
                registry.build_registry()

        finally:
            registry.load_openai_tools = original

    def test_invalid_openai_shape_rejected(self):

        with self.assertRaises(ValueError):
            normalize_openai_tool({'type': 'function'})

        with self.assertRaises(ValueError):
            normalize_openai_tool(
                {
                    'type': 'tool',
                    'function': {
                        'name': 'x',
                        'parameters': {'type': 'object'},
                    },
                }
            )


if __name__ == '__main__':
    unittest.main()
