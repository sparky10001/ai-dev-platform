#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from runtime.errors import EventLedgerError


BOUNDARY_RULES: dict[str, dict[str, Any]] = {
    "runtime/engine.py": {
        "forbidden_imports": {
            "control-plane",
        }
    },
    "runtime/adapter_gateway.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.run_lifecycle",
            "runtime.trace_pipeline",
            "runtime.replay",
            "runtime.evals",
            "runtime.registry",
            "control-plane",
        }
    },
    "runtime/run_lifecycle.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.adapter_gateway",
            "runtime.replay",
            "runtime.evals",
            "runtime.registry",
            "control-plane",
        }
    },
    "runtime/event_ledger.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.replay",
            "runtime.evals",
            "runtime.registry",
            "control-plane",
        }
    },
    "runtime/trace_pipeline.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.replay",
            "runtime.evals",
            "runtime.registry",
            "control-plane",
        }
    },
    "runtime/replay.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.adapter_gateway",
            "runtime.run_lifecycle",
        }
    },
    "runtime/evals.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.adapter_gateway",
            "runtime.run_lifecycle",
        }
    },
    "runtime/registry.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.adapter_gateway",
            "runtime.run_lifecycle",
        }
    },
    "runtime/datasets.py": {
        "forbidden_imports": {
            "runtime.engine",
            "runtime.adapter_gateway",
            "runtime.run_lifecycle",
        }
    },
}


def _is_forbidden(import_name: str, forbidden_set: set[str]) -> bool:
    for forbidden in forbidden_set:
        if forbidden == "control-plane":
            if import_name.startswith("control-plane") or import_name.startswith("control_plane"):
                return True
            continue
        if import_name == forbidden or import_name.startswith(f"{forbidden}."):
            return True
    return False


def _violation(module: str, line: int, import_name: str, message: str) -> dict[str, Any]:
    return {
        "module": module,
        "line": int(line),
        "type": "forbidden_import",
        "import": import_name,
        "message": message,
    }


def _module_report(module_rel: str, tree: ast.AST, forbidden_imports: set[str]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if _is_forbidden(name, forbidden_imports):
                    violations.append(
                        _violation(module_rel, node.lineno, name, f"Forbidden import for {module_rel}: {name}")
                    )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _is_forbidden(mod, forbidden_imports):
                violations.append(
                    _violation(module_rel, node.lineno, mod, f"Forbidden import for {module_rel}: {mod}")
                )

    return {
        "module": module_rel,
        "status": "ok" if not violations else "violations",
        "violations": sorted(violations, key=lambda item: (item["line"], item["import"])),
    }


def _read_tree(path: Path) -> ast.AST:
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path))


def _audit_control_plane_engine_imports(root: Path) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    cp_root = root / "control-plane"
    if not cp_root.exists():
        return violations

    for path in sorted(cp_root.rglob("*.py")):
        tree = _read_tree(path)
        module_rel = str(path.relative_to(root))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "runtime.engine" or name.startswith("runtime.engine."):
                        violations.append(
                            _violation(module_rel, node.lineno, name, "control-plane must not import runtime.engine")
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "runtime.engine" or mod.startswith("runtime.engine."):
                    violations.append(
                        _violation(module_rel, node.lineno, mod, "control-plane must not import runtime.engine")
                    )

    return violations


def audit_import_boundaries(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root).resolve()
    modules: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for module_rel, rule in sorted(BOUNDARY_RULES.items()):
        path = root_path / module_rel
        if not path.exists():
            continue
        tree = _read_tree(path)
        report = _module_report(module_rel, tree, set(rule.get("forbidden_imports", set())))
        modules.append(report)
        violations.extend(report["violations"])

    cp_violations = _audit_control_plane_engine_imports(root_path)
    if cp_violations:
        modules.append(
            {
                "module": "control-plane",
                "status": "violations",
                "violations": sorted(cp_violations, key=lambda item: (item["module"], item["line"])),
            }
        )
        violations.extend(cp_violations)
    else:
        modules.append({"module": "control-plane", "status": "ok", "violations": []})

    layers = {
        "execution": [
            "runtime/engine.py",
            "runtime/adapter_gateway.py",
            "runtime/run_lifecycle.py",
            "runtime/trace_pipeline.py",
            "runtime/event_ledger.py",
        ],
        "derived": [
            "runtime/replay.py",
            "runtime/evals.py",
            "runtime/registry.py",
        ],
        "projection_writer": ["runtime/datasets.py"],
        "consumers": ["control-plane"],
    }

    return {
        "status": "ok" if not violations else "violations",
        "layers": layers,
        "modules": modules,
        "violations": sorted(violations, key=lambda item: (item["module"], item["line"], item["import"])),
    }


def audit_runtime_boundaries() -> dict[str, Any]:
    return audit_import_boundaries(Path(__file__).resolve().parent.parent)


def boundary_violations(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("violations", []))


def validate_runtime_boundaries() -> None:
    report = audit_runtime_boundaries()
    violations = boundary_violations(report)
    if violations:
        first = violations[0]
        raise EventLedgerError(
            f"Runtime boundary violations detected: {first['module']}:{first['line']} {first['import']}"
        )
