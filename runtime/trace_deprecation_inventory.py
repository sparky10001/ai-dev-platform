#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.trace_compatibility import TRACE_PATTERNS, classify_trace_dependency


CATEGORY_NAMES = (
    'compatibility_retained',
    'operational_dependency',
    'legacy_runtime_dependency',
    'future_deprecation_candidate',
    'future_removal_candidate',
    'documentation_only',
    'test_only',
    'historical_reference',
)

LEGACY_RUNTIME_PATHS = {
    'runtime/loader.py',
    'runtime/run.py',
    'runtime/events.py',
}

COMPATIBILITY_RETAINED_PATHS = {
    'runtime/replay.py',
    'runtime/evals.py',
    'runtime/registry.py',
    'runtime/event_loader.py',
    'runtime/event_ledger.py',
    'runtime/authority_policy.py',
    'runtime/dual_authority_validation.py',
    'control-plane/core/runtime_events.py',
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _requires_cutover(category: str) -> bool:
    return category in {
        'compatibility_retained',
        'legacy_runtime_dependency',
        'future_deprecation_candidate',
        'future_removal_candidate',
    }


def _requires_validation_window(category: str) -> bool:
    return category in {
        'compatibility_retained',
        'legacy_runtime_dependency',
        'future_deprecation_candidate',
        'future_removal_candidate',
        'operational_dependency',
    }


def _entry(path: str, category: str, reason: str, notes: str) -> dict[str, Any]:
    return {
        'path': path,
        'category': category,
        'reason': reason,
        'safe_to_remove_now': False,
        'requires_cutover': _requires_cutover(category),
        'requires_validation_window': _requires_validation_window(category),
        'notes': notes,
    }


def _is_historical(content: str) -> bool:
    lowered = content.lower()
    return any(token in lowered for token in ('phase 3.6', 'phase 3.7', 'phase 3.8', 'phase 3.9'))


def _classify(path: str, content: str) -> dict[str, Any]:
    dep = classify_trace_dependency(path, content=content)
    classification = dep.get('classification', 'compatibility_only')

    if path.startswith('docs/'):
        if _is_historical(content):
            return _entry(path, 'historical_reference', 'Historical migration/reference text mentioning trace compatibility.', 'Retain for migration history and context.')
        return _entry(path, 'documentation_only', 'Documentation-only trace reference.', 'No runtime behavior impact.')

    if '/tests/' in path or path.startswith('tests/'):
        return _entry(path, 'test_only', 'Trace reference used for test compatibility coverage.', 'Retain to preserve replay and compatibility assertions.')

    if path.startswith('scripts/maintenance/') or path.startswith('scripts/tests/'):
        return _entry(path, 'operational_dependency', 'Operational tooling depends on trace artifacts/terminology.', 'Operationally retained until deprecation execution phase.')

    if path in LEGACY_RUNTIME_PATHS:
        return _entry(path, 'legacy_runtime_dependency', 'Legacy runtime path with direct trace coupling.', 'Migrate only through additive compatibility planning.')

    if path in COMPATIBILITY_RETAINED_PATHS:
        return _entry(path, 'compatibility_retained', 'Active compatibility scaffolding preserving trace/ledger coexistence.', 'Retain until explicit trace retirement plan is executed.')

    if classification == 'cutover_blocker':
        return _entry(path, 'future_deprecation_candidate', 'Current trace dependency may become deprecation target after cutover readiness.', 'Not safe to remove now; requires cutover plan and validation window.')

    if path.startswith('runtime/') or path.startswith('control-plane/'):
        return _entry(path, 'future_deprecation_candidate', 'Compatibility-era trace reference in active code path.', 'Evaluate only after authority/default migration milestones.')

    return _entry(path, 'future_removal_candidate', 'Trace terminology/reference appears removable in future cleanup phase.', 'Only consider after compatibility retirement plan.')


def _scan(base: Path) -> list[dict[str, Any]]:
    roots = [
        base / 'runtime',
        base / 'control-plane',
        base / 'scripts',
        base / 'docs',
    ]
    entries: list[dict[str, Any]] = []

    for root in roots:
        if not root.exists():
            continue
        for fp in sorted(root.rglob('*')):
            if not fp.is_file() or '__pycache__' in fp.parts:
                continue
            if fp.suffix not in {'.py', '.md', '.sh', '.json', '.yaml', '.yml', '.txt'}:
                continue
            try:
                content = fp.read_text(encoding='utf-8')
            except Exception:
                continue
            if not any(token in content for token in TRACE_PATTERNS):
                continue
            rel = str(fp.relative_to(base)).replace('\\', '/')
            entries.append(_classify(rel, content))

    return sorted(entries, key=lambda item: (item.get('path', ''), item.get('category', '')))


def _summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {name: 0 for name in CATEGORY_NAMES}
    for item in entries:
        category = item.get('category')
        if category in counts:
            counts[category] += 1

    return {
        'total_references': len(entries),
        'compatibility_retained_count': counts['compatibility_retained'],
        'operational_dependency_count': counts['operational_dependency'],
        'legacy_runtime_dependency_count': counts['legacy_runtime_dependency'],
        'future_deprecation_candidate_count': counts['future_deprecation_candidate'],
        'future_removal_candidate_count': counts['future_removal_candidate'],
        'documentation_only_count': counts['documentation_only'],
        'test_only_count': counts['test_only'],
        'historical_reference_count': counts['historical_reference'],
    }


def trace_deprecation_candidates(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    categories = inventory.get('categories', {})
    items = list(categories.get('future_deprecation_candidate', [])) + list(categories.get('future_removal_candidate', []))
    return sorted(items, key=lambda item: (item.get('path', ''), item.get('category', '')))


def trace_compatibility_retained(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    categories = inventory.get('categories', {})
    items = list(categories.get('compatibility_retained', [])) + list(categories.get('legacy_runtime_dependency', []))
    return sorted(items, key=lambda item: (item.get('path', ''), item.get('category', '')))


def trace_operational_dependencies(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    categories = inventory.get('categories', {})
    return sorted(list(categories.get('operational_dependency', [])), key=lambda item: (item.get('path', ''), item.get('category', '')))


def build_trace_deprecation_inventory(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root).resolve() if root is not None else Path('.').resolve()
    entries = _scan(base)

    categories: dict[str, list[dict[str, Any]]] = {name: [] for name in CATEGORY_NAMES}
    for item in entries:
        category = item.get('category')
        if category in categories:
            categories[category].append(item)

    inventory = {
        'status': 'informational',
        'summary': _summary(entries),
        'categories': categories,
        'candidates': trace_deprecation_candidates({'categories': categories}),
        'retained': trace_compatibility_retained({'categories': categories}),
        'operational': trace_operational_dependencies({'categories': categories}),
        'generated_at': _now_iso(),
    }
    return inventory
