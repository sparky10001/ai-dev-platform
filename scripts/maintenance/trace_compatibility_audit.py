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

from runtime.trace_compatibility import audit_trace_compatibility, summarize_trace_dependencies

EXIT_OK = 0
EXIT_BLOCKERS = 1
EXIT_ERROR = 2


def _print_human(report: dict[str, Any], summary_only: bool) -> None:
    summary = summarize_trace_dependencies(report)
    print(f"status={summary['status']} total_dependencies={summary['total_dependencies']}")
    print(
        "  compatibility_only={compat} cutover_blocker={blocker} legacy_runtime={legacy} "
        "test_only={test} docs_only={docs} operational_tooling={ops}".format(
            compat=summary["summary"].get("compatibility_only_count", 0),
            blocker=summary["summary"].get("cutover_blocker_count", 0),
            legacy=summary["summary"].get("legacy_runtime_dependency_count", 0),
            test=summary["summary"].get("test_only_count", 0),
            docs=summary["summary"].get("documentation_only_count", 0),
            ops=summary["summary"].get("operational_tooling_count", 0),
        )
    )

    if summary_only:
        return

    cats = report.get("categories", {})

    print("\n[cutover_blockers]")
    for dep in cats.get("cutover_blocker", []):
        print(f"- {dep['path']}: {dep['reason']}")

    print("\n[compatibility_only]")
    for dep in cats.get("compatibility_only", []):
        print(f"- {dep['path']}")

    print("\n[legacy_runtime_dependency]")
    for dep in cats.get("legacy_runtime_dependency", []):
        print(f"- {dep['path']}")

    print("\n[test_only/docs/ops]")
    for key in ("test_only", "documentation_only", "operational_tooling"):
        for dep in cats.get(key, []):
            print(f"- {key}: {dep['path']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace compatibility dependency audit")
    parser.add_argument("--json", action="store_true", help="Emit full JSON report")
    parser.add_argument("--summary", action="store_true", help="Emit summary view")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when cutover blockers are present")
    parser.add_argument("--root", default=".", help="Repository root to audit")
    args = parser.parse_args()

    try:
        report = audit_trace_compatibility(args.root)
    except Exception as exc:
        payload = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR

    blockers = report.get("summary", {}).get("cutover_blocker_count", 0)

    if args.json:
        payload = summarize_trace_dependencies(report) if args.summary else report
        print(json.dumps(payload, sort_keys=True))
    else:
        _print_human(report, summary_only=args.summary)

    if args.strict and blockers > 0:
        return EXIT_BLOCKERS
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
