#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.trace_deprecation_inventory import (
    CATEGORY_NAMES,
    build_trace_deprecation_inventory,
    trace_compatibility_retained,
    trace_deprecation_candidates,
    trace_operational_dependencies,
)

EXIT_OK = 0
EXIT_STRICT_INVALID = 1
EXIT_ERROR = 2


def _validate_inventory(inventory: dict[str, Any]) -> bool:
    if inventory.get('status') != 'informational':
        return False
    categories = inventory.get('categories')
    if not isinstance(categories, dict):
        return False
    for name in CATEGORY_NAMES:
        if name not in categories:
            return False
    return True


def _print_summary(inventory: dict[str, Any]) -> None:
    summary = inventory.get('summary', {})
    print(
        'status={status} total={total} candidates={candidates} retained={retained} operational={operational}'.format(
            status=inventory.get('status'),
            total=summary.get('total_references', 0),
            candidates=summary.get('future_deprecation_candidate_count', 0) + summary.get('future_removal_candidate_count', 0),
            retained=summary.get('compatibility_retained_count', 0) + summary.get('legacy_runtime_dependency_count', 0),
            operational=summary.get('operational_dependency_count', 0),
        )
    )


def _print_items(items: list[dict[str, Any]]) -> None:
    if not items:
        print('none')
        return
    for item in items:
        print('{path} [{category}]'.format(path=item.get('path'), category=item.get('category')))
        print('  reason={reason}'.format(reason=item.get('reason')))


def main() -> int:
    parser = argparse.ArgumentParser(description='Trace compatibility deprecation inventory (informational)')
    parser.add_argument('--summary', action='store_true', help='Print summary output')
    parser.add_argument('--json', action='store_true', help='Emit full JSON payload')
    parser.add_argument('--candidates', action='store_true', help='Print future deprecation/removal candidates')
    parser.add_argument('--retained', action='store_true', help='Print retained compatibility references')
    parser.add_argument('--operational', action='store_true', help='Print operational dependencies')
    parser.add_argument('--strict', action='store_true', help='Fail only on malformed inventory state')
    parser.add_argument('--root', default='.', help='Repository root to scan')
    args = parser.parse_args()

    try:
        inventory = build_trace_deprecation_inventory(args.root)

        if args.strict and not _validate_inventory(inventory):
            print('error: malformed inventory state')
            return EXIT_STRICT_INVALID

        if args.json:
            print(json.dumps(inventory, sort_keys=True))
            return EXIT_OK

        if args.candidates:
            _print_items(trace_deprecation_candidates(inventory))
            return EXIT_OK

        if args.retained:
            _print_items(trace_compatibility_retained(inventory))
            return EXIT_OK

        if args.operational:
            _print_items(trace_operational_dependencies(inventory))
            return EXIT_OK

        _print_summary(inventory)
        return EXIT_OK
    except Exception as exc:
        if args.json:
            print(json.dumps({'status': 'error', 'reason': str(exc)}, sort_keys=True))
        else:
            print(f'error: {exc}')
        return EXIT_ERROR


if __name__ == '__main__':
    raise SystemExit(main())
