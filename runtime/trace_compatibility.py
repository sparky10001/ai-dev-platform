#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


TRACE_PATTERNS = (
    "trace.jsonl",
    "load_trace",
    "replay_trace",
    "iter_trace_events",
    "trace_pipeline",
)

CATEGORY_NAMES = (
    "compatibility_only",
    "cutover_blocker",
    "legacy_runtime_dependency",
    "test_only",
    "documentation_only",
    "operational_tooling",
)

LEGACY_RUNTIME_PATHS = {"runtime/loader.py", "runtime/run.py"}

COMPATIBILITY_RUNTIME_PATHS = {
    "runtime/replay.py",
    "runtime/evals.py",
    "runtime/registry.py",
    "runtime/event_ledger.py",
    "runtime/ledger_drift.py",
    "runtime/ledger_corruption.py",
    "runtime/ledger_health.py",
    "runtime/trace_pipeline.py",
    "runtime/engine.py",
    "runtime/events.py",
}


def _extract_trace_usage(content: str) -> list[str]:
    return [token for token in TRACE_PATTERNS if token in content]


def _extract_imports(content: str) -> list[str]:
    imports: list[str] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return imports


def _reason_for(path: str, classification: str) -> str:
    reasons = {
        "compatibility_only": "Trace reference is for transitional compatibility, parity, or dual-source support.",
        "cutover_blocker": "Trace is assumed as mandatory runtime authority and blocks default-trace removal.",
        "legacy_runtime_dependency": "Legacy runtime module/path has direct trace coupling that should be migrated later.",
        "test_only": "Trace usage is isolated to test validation and does not impact production runtime authority.",
        "documentation_only": "Trace mention is informational documentation or architecture explanation.",
        "operational_tooling": "Trace usage is operational maintenance/audit tooling, not runtime execution authority.",
    }
    return f"{reasons[classification]} ({path})"


def _is_true_cutover_blocker(path_str: str, content: str) -> bool:
    # True blockers are runtime modules with explicit trace-only artifact assumptions.
    if not path_str.startswith("runtime/") or "/tests/" in path_str:
        return False

    if path_str in LEGACY_RUNTIME_PATHS:
        return False

    if path_str in COMPATIBILITY_RUNTIME_PATHS:
        return False

    has_trace_artifact = "trace.jsonl" in content
    has_ledger_artifact = "ledger.jsonl" in content

    # Trace-only artifact access with no ledger alternative remains a blocker.
    if has_trace_artifact and not has_ledger_artifact:
        return True

    return False


def classify_trace_dependency(path: str | Path, content: str | None = None) -> dict[str, Any]:
    p = Path(path)
    path_str = str(p).replace("\\", "/")

    if content is None:
        content = p.read_text(encoding="utf-8")

    trace_usage = _extract_trace_usage(content)
    imports = _extract_imports(content) if path_str.endswith(".py") else []

    if not trace_usage:
        return {
            "path": path_str,
            "classification": "compatibility_only",
            "reason": "No trace dependency usage found.",
            "trace_usage": [],
            "resolution_hint": "No action required.",
        }

    if path_str.startswith("docs/") or path_str.endswith(".md"):
        cls = "documentation_only"
        hint = "Documentation-only reference; keep until migration docs are updated."
    elif "/tests/" in path_str or path_str.startswith("tests/"):
        cls = "test_only"
        hint = "Test-only trace reference; retain for compatibility coverage."
    elif path_str.startswith("scripts/maintenance/"):
        cls = "operational_tooling"
        hint = "Operational audit/tooling reference; retain for observability and diagnostics."
    elif path_str in LEGACY_RUNTIME_PATHS:
        cls = "legacy_runtime_dependency"
        hint = "Legacy runtime coupling; migrate through additive compatibility steps, not cutover phase."
    elif _is_true_cutover_blocker(path_str, content):
        cls = "cutover_blocker"
        hint = "Introduce ledger-aware source resolution or compatibility abstraction before cutover."
    elif path_str.startswith("control-plane/"):
        if "runtime.engine" in imports:
            cls = "cutover_blocker"
            hint = "Control-plane must avoid importing runtime engine internals directly."
        else:
            cls = "compatibility_only"
            hint = "Compatibility-only trace consumer; acceptable until trace retirement planning."
    elif path_str.startswith("scripts/") and not path_str.startswith("scripts/tests/"):
        cls = "compatibility_only"
        hint = "Script-level compatibility reference; not a runtime cutover blocker."
    else:
        cls = "compatibility_only"
        hint = "Compatibility scaffolding; maintain until cutover execution phase."

    return {
        "path": path_str,
        "classification": cls,
        "reason": _reason_for(path_str, cls),
        "trace_usage": trace_usage,
        "resolution_hint": hint,
    }


def audit_trace_compatibility(root: str | Path = ".") -> dict[str, Any]:
    base = Path(root).resolve()
    search_roots = [base / "runtime", base / "scripts", base / "control-plane", base / "docs"]

    dependencies: list[dict[str, Any]] = []

    for search_root in search_roots:
        if not search_root.exists():
            continue
        for fp in sorted(search_root.rglob("*")):
            if not fp.is_file() or "__pycache__" in fp.parts:
                continue
            if fp.suffix not in {".py", ".md", ".sh", ".json", ".yaml", ".yml", ".txt"}:
                continue
            try:
                content = fp.read_text(encoding="utf-8")
            except Exception:
                continue
            if not any(token in content for token in TRACE_PATTERNS):
                continue
            rel = fp.relative_to(base)
            dependencies.append(classify_trace_dependency(rel, content=content))

    dependencies = sorted(dependencies, key=lambda item: item["path"])

    categories: dict[str, list[dict[str, Any]]] = {name: [] for name in CATEGORY_NAMES}
    for dep in dependencies:
        categories[dep["classification"]].append(dep)

    summary = {
        "compatibility_only_count": len(categories["compatibility_only"]),
        "cutover_blocker_count": len(categories["cutover_blocker"]),
        "legacy_runtime_dependency_count": len(categories["legacy_runtime_dependency"]),
        "test_only_count": len(categories["test_only"]),
        "documentation_only_count": len(categories["documentation_only"]),
        "operational_tooling_count": len(categories["operational_tooling"]),
    }

    status = "ok"
    if summary["cutover_blocker_count"] > 0:
        status = "blocked"
    elif summary["legacy_runtime_dependency_count"] > 0:
        status = "warning"

    cutover_blockers = [
        {
            "path": dep["path"],
            "reason": dep["reason"],
            "resolution_hint": dep.get("resolution_hint", "Add ledger-compatible source handling."),
        }
        for dep in categories["cutover_blocker"]
    ]

    return {
        "status": status,
        "total_dependencies": len(dependencies),
        "categories": categories,
        "summary": summary,
        "dependencies": dependencies,
        "cutover_blockers": cutover_blockers,
    }


def summarize_trace_dependencies(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status", "warning"),
        "total_dependencies": report.get("total_dependencies", 0),
        "summary": dict(report.get("summary", {})),
        "cutover_blockers": list(report.get("cutover_blockers", [])),
    }


def validate_trace_cutover_readiness() -> None:
    report = audit_trace_compatibility()
    blockers = report.get("cutover_blockers", [])
    if blockers:
        paths = ", ".join(item.get("path", "<unknown>") for item in blockers)
        raise RuntimeError(f"Trace cutover blockers detected: {paths}")


def trace_deprecation_inventory_summary(root: str | Path = '.') -> dict[str, Any]:
    # Lazy import avoids import cycles; this is informational only.
    from runtime.trace_deprecation_inventory import build_trace_deprecation_inventory

    inventory = build_trace_deprecation_inventory(root)
    return {
        'status': inventory.get('status', 'informational'),
        'summary': dict(inventory.get('summary', {})),
        'candidate_count': len(inventory.get('candidates', [])),
        'retained_count': len(inventory.get('retained', [])),
        'operational_count': len(inventory.get('operational', [])),
    }
