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


def _extract_trace_usage(content: str) -> list[str]:
    usage: list[str] = []
    for token in TRACE_PATTERNS:
        if token in content:
            usage.append(token)
    return usage


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
            module = node.module or ""
            imports.append(module)
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
        }

    if path_str.startswith("docs/") or path_str.endswith(".md"):
        cls = "documentation_only"
    elif "/tests/" in path_str or path_str.startswith("tests/"):
        cls = "test_only"
    elif path_str.startswith("scripts/maintenance/"):
        cls = "operational_tooling"
    elif path_str in {"runtime/loader.py", "runtime/run.py"}:
        cls = "legacy_runtime_dependency"
    elif path_str.startswith("runtime/"):
        blocker_paths = {
            "runtime/run.py",
            "runtime/engine.py",
            "runtime/events.py",
            "runtime/trace_pipeline.py",
        }
        if path_str in blocker_paths:
            cls = "cutover_blocker"
        else:
            cls = "compatibility_only"
    elif path_str.startswith("control-plane/"):
        # control-plane trace coupling is currently compatibility but blocks full trace retirement
        if "runtime.engine" in imports:
            cls = "cutover_blocker"
        else:
            cls = "compatibility_only"
    elif path_str.startswith("scripts/"):
        if path_str.startswith("scripts/tests/"):
            cls = "test_only"
        else:
            cls = "compatibility_only"
    else:
        cls = "compatibility_only"

    return {
        "path": path_str,
        "classification": cls,
        "reason": _reason_for(path_str, cls),
        "trace_usage": trace_usage,
    }


def audit_trace_compatibility(root: str | Path = ".") -> dict[str, Any]:
    base = Path(root).resolve()
    search_roots = [base / "runtime", base / "scripts", base / "control-plane", base / "docs"]

    dependencies: list[dict[str, Any]] = []

    for search_root in search_roots:
        if not search_root.exists():
            continue
        for fp in sorted(search_root.rglob("*")):
            if not fp.is_file():
                continue
            if "__pycache__" in fp.parts:
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

    return {
        "status": status,
        "total_dependencies": len(dependencies),
        "categories": categories,
        "summary": summary,
        "dependencies": dependencies,
    }


def summarize_trace_dependencies(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status", "warning"),
        "total_dependencies": report.get("total_dependencies", 0),
        "summary": dict(report.get("summary", {})),
    }


def validate_trace_cutover_readiness() -> None:
    report = audit_trace_compatibility()
    blockers = report.get("categories", {}).get("cutover_blocker", [])
    if blockers:
        paths = ", ".join(item.get("path", "<unknown>") for item in blockers)
        raise RuntimeError(f"Trace cutover blockers detected: {paths}")
