#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.derived_purity import audit_module_purity, audit_runtime_derived_purity, derived_purity_violations


EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit runtime derived-system purity")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when violations are found")
    parser.add_argument("--module", type=str, default=None, help="Audit one module path")
    args = parser.parse_args()

    try:
        if args.module:
            report = audit_module_purity(Path(args.module))
            payload = {
                "status": report["status"],
                "modules": [report],
                "violations": report["violations"],
                "classifications": {},
            }
        else:
            payload = audit_runtime_derived_purity()
    except Exception as exc:
        error = {"status": "error", "reason": str(exc)}
        if args.json:
            print(json.dumps(error, sort_keys=True))
        else:
            print(f"error: {exc}")
        return EXIT_ERROR

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"status: {payload['status']}")
        print(f"modules: {len(payload.get('modules', []))}")
        violations = derived_purity_violations(payload)
        print(f"violations: {len(violations)}")
        if violations:
            first = violations[0]
            print(
                f"first_violation: {first['module']}:{first['line']} {first['type']} {first['symbol']}"
            )

    if args.strict and derived_purity_violations(payload):
        return EXIT_VIOLATIONS

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
