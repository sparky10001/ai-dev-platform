#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

CONTROL_PLANE_ROOT = Path(__file__).resolve().parents[1]
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

from core.dag.validator import validate_dag
from core.planner.models import PlannerRequest
from core.planner.planner import deterministic_plan
from core.planner.planner import plan_task


class DagPlannerTests(unittest.TestCase):
    def test_planner_request_rejects_empty_task(self):
        with self.assertRaises(Exception):
            PlannerRequest(task="   ")

    def test_noop_strategy_returns_noop_dag(self):
        result = plan_task({"task": "anything", "strategy": "noop"})
        self.assertEqual(result.status, "success")
        self.assertEqual(result.dag.dag_id, "plan_noop")

    def test_create_file_and_list_produces_expected_dag(self):
        result = plan_task("Create a file called hello.txt with content 'hi' and then list files")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.dag.dag_id, "plan_write_list")
        write = next(n for n in result.dag.nodes if n.id == "write")
        list_node = next(n for n in result.dag.nodes if n.id == "list")
        self.assertEqual(write.tool, "write_file")
        self.assertEqual(list_node.depends_on, ["write"])

    def test_list_and_show_files_tasks(self):
        self.assertEqual(plan_task("list files").dag.dag_id, "plan_list_files")
        self.assertEqual(plan_task("show files").dag.dag_id, "plan_list_files")

    def test_read_file_task(self):
        result = plan_task("read README.md")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.dag.dag_id, "plan_read_file")
        self.assertEqual(result.dag.nodes[0].args.get("path"), "README.md")

    def test_unsupported_task_falls_back_to_noop(self):
        result = plan_task("do something advanced")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.dag.dag_id, "plan_noop")

    def test_plan_task_accepts_plain_string_and_dict(self):
        self.assertEqual(plan_task("list files").status, "success")
        self.assertEqual(plan_task({"task": "show files"}).status, "success")

    def test_all_generated_dags_validate(self):
        dags = [
            deterministic_plan("Create a file called hello.txt with content 'hi' and then list files"),
            deterministic_plan("list files"),
            deterministic_plan("read README.md"),
            deterministic_plan("unsupported task"),
        ]
        for dag in dags:
            validated = validate_dag(dag.model_dump())
            self.assertEqual(validated.dag_id, dag.dag_id)

    def test_deterministic_planner_never_executes_tools_for_fallback(self):
        import core.planner.planner as planner_mod

        original = planner_mod.validate_tool_node

        def fail_if_called(*_args, **_kwargs):
            raise RuntimeError("tool validation reached")

        planner_mod.validate_tool_node = fail_if_called
        try:
            result = plan_task("unsupported task")
            self.assertEqual(result.status, "success")
            self.assertEqual(result.dag.dag_id, "plan_noop")
        finally:
            planner_mod.validate_tool_node = original

    def test_unsupported_strategy_returns_error_result(self):
        result = plan_task({"task": "list files", "strategy": "custom"})
        self.assertEqual(result.status, "error")


if __name__ == "__main__":
    unittest.main()
