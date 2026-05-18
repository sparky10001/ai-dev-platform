#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.boundary_audit import audit_import_boundaries, audit_runtime_boundaries, boundary_violations


EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2

def _resolve_module_scope(module_arg: str) -> tuple[Path, str]:
    path = Path(module_arg).resolve()
    parts = list(path.parts)

    for anchor in ("runtime", "control-plane"):
        if anchor in parts:
            idx = parts.index(anchor)
            root = Path(*parts[:idx]) if idx > 0 else Path("/")
            rel = "/".join(parts[idx:])
            return root, rel

    if path.is_relative_to(ROOT):
        return ROOT, str(path.relative_to(ROOT))

    return path.parent, path.name


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit runtime boundary imports")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on boundary violations")
    parser.add_argument("--module", type=str, default=None, help="Focused module path audit")
    args = parser.parse_args()

    try:
        if args.module:
            root, module_rel = _resolve_module_scope(args.module)
            full = audit_import_boundaries(root)
            selected = [m for m in full.get("modules", []) if m.get("module") == module_rel]
            if not selected:
                selected = [{"module": module_rel, "status": "ok", "violations": []}]
            payload = {
                "status": "ok" if not selected[0]["violations"] else "violations",
                "layers": full.get("layers", {}),
                "modules": selected,
                "violations": selected[0]["violations"],
            }
        else:
            payload = audit_runtime_boundaries()
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
        print(f"violations: {len(boundary_violations(payload))}")
        if boundary_violations(payload):
            first = boundary_violations(payload)[0]
            print(f"first_violation: {first['module']}:{first['line']} {first['import']}")

    if args.strict and boundary_violations(payload):
        return EXIT_VIOLATIONS

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
