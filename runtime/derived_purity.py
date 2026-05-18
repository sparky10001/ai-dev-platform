#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from runtime.errors import EventLedgerError


DEFAULT_DERIVED_MODULES = [
    "runtime/replay.py",
    "runtime/evals.py",
    "runtime/registry.py",
    "runtime/ledger_drift.py",
]

DATASET_MODULE = "runtime/datasets.py"

FORBIDDEN_IMPORTS = {
    "runtime.engine",
    "runtime.run",
    "scripts.tool_executor",
}

RUNTIME_SOURCE_ARTIFACTS = {
    "trace.jsonl",
    "ledger.jsonl",
    "run.json",
    "result.json",
}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _mode_arg(call: ast.Call) -> str | None:
    if len(call.args) >= 2:
        mode = _const_str(call.args[1])
        if mode is not None:
            return mode
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = _const_str(kw.value)
            if mode is not None:
                return mode
    return None


def _has_runtime_source_literal(call: ast.Call) -> bool:
    for arg in call.args:
        val = _const_str(arg)
        if val is None:
            continue
        for marker in RUNTIME_SOURCE_ARTIFACTS:
            if marker in val:
                return True
    return False


def _violation(module: str, line: int, vtype: str, symbol: str, message: str) -> dict[str, Any]:
    return {
        "module": module,
        "line": line,
        "type": vtype,
        "symbol": symbol,
        "message": message,
    }


def audit_module_purity(module_path: str | Path, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    module = str(module_path)
    path = Path(module_path)
    rules = rules or {}

    allow_projection_writes = bool(rules.get("allow_projection_writes", False))
    forbidden_imports = set(rules.get("forbidden_imports", FORBIDDEN_IMPORTS))

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    violations: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if any(name == imp or name.startswith(f"{imp}.") for imp in forbidden_imports):
                    violations.append(
                        _violation(module, node.lineno, "forbidden_import", name, f"Forbidden import: {name}")
                    )
                if name == "subprocess":
                    violations.append(
                        _violation(module, node.lineno, "forbidden_subprocess", name, "subprocess usage is forbidden")
                    )

        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if any(mod == imp or mod.startswith(f"{imp}.") for imp in forbidden_imports):
                violations.append(
                    _violation(module, node.lineno, "forbidden_import", mod, f"Forbidden import: {mod}")
                )
            if mod == "subprocess":
                violations.append(
                    _violation(module, node.lineno, "forbidden_subprocess", mod, "subprocess usage is forbidden")
                )

        if not isinstance(node, ast.Call):
            continue

        name = _call_name(node.func)

        if name.startswith("subprocess."):
            violations.append(
                _violation(module, node.lineno, "forbidden_subprocess", name, "subprocess invocation is forbidden")
            )

        is_write = False

        if name == "open":
            mode = _mode_arg(node)
            if mode and ("w" in mode or "a" in mode):
                is_write = True

        if name in {"write_text", "write_bytes"} or name.endswith(".write_text") or name.endswith(".write_bytes"):
            is_write = True

        if name in {"os.remove", "os.unlink", "shutil.rmtree", "os.makedirs"}:
            is_write = True

        if name in {"unlink", "mkdir"} or name.endswith(".unlink") or name.endswith(".mkdir"):
            is_write = True

        if name == "json.dump":
            is_write = True

        if is_write:
            if allow_projection_writes:
                if _has_runtime_source_literal(node):
                    violations.append(
                        _violation(
                            module,
                            node.lineno,
                            "source_artifact_write",
                            name,
                            "Projection writer must not mutate runtime source artifacts",
                        )
                    )
            else:
                violations.append(
                    _violation(module, node.lineno, "forbidden_write", name, f"Forbidden write operation: {name}")
                )

    return {
        "module": module,
        "status": "ok" if not violations else "violations",
        "violations": sorted(violations, key=lambda item: (item["line"], item["type"], item["symbol"])),
    }


def derived_purity_violations(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("violations", []))


def audit_runtime_derived_purity() -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for module in DEFAULT_DERIVED_MODULES:
        module_report = audit_module_purity(module)
        modules.append(module_report)
        violations.extend(module_report["violations"])

    dataset_report = audit_module_purity(DATASET_MODULE, rules={"allow_projection_writes": True})
    modules.append(dataset_report)
    violations.extend(dataset_report["violations"])

    return {
        "status": "ok" if not violations else "violations",
        "modules": modules,
        "violations": violations,
        "classifications": {
            DATASET_MODULE: "projection_writer",
        },
    }


def validate_runtime_derived_purity() -> None:
    report = audit_runtime_derived_purity()
    violations = derived_purity_violations(report)
    if violations:
        first = violations[0]
        raise EventLedgerError(
            f"Derived-system purity violations detected: {first['module']}:{first['line']} {first['type']}"
        )
