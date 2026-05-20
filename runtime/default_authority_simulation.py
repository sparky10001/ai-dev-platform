#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.authority_policy import runtime_authority_transition_state
from runtime.dual_authority_validation import evaluate_dual_authority_validation
from runtime.ledger_authority_matrix import evaluate_ledger_authority_readiness
from runtime.loader import RUNS_DIR
from runtime.trace_compatibility import summarize_trace_dependencies
from runtime.trace_deprecation_inventory import build_trace_deprecation_inventory


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_dirs(runs_root: Path, recent: int | None = None) -> list[Path]:
    if not runs_root.exists():
        return []
    runs = [p for p in runs_root.iterdir() if p.is_dir()]
    runs = sorted(runs, key=lambda p: (-p.stat().st_mtime, p.name))
    if recent is not None:
        runs = runs[: max(0, recent)]
    return runs


def _resolve_target(run_or_path: str | Path | None, runs_root: Path) -> Path:
    if run_or_path is None:
        runs = _run_dirs(runs_root, recent=1)
        if not runs:
            raise FileNotFoundError(f"No run directories found under: {runs_root}")
        return runs[0]
    candidate = Path(run_or_path)
    if candidate.exists():
        return candidate
    return runs_root / str(run_or_path)


def _status_from_bool(ok: bool) -> str:
    return "ready" if ok else "blocked"


def _build_simulation_payload() -> dict[str, Any]:
    transition = runtime_authority_transition_state()
    rollback_supported = bool(transition.get("rollback_supported", False))
    return {
        "simulated_default": "ledger",
        "actual_default": str(transition.get("current_default", "trace")),
        "authority_switch_performed": False,
        "trace_emission_preserved": bool(transition.get("trace_emission_enabled", True)),
        "rollback_supported": rollback_supported,
    }


def _control_plane_status(compatibility: dict[str, Any]) -> dict[str, Any]:
    blockers = int(compatibility.get("summary", {}).get("cutover_blocker_count", 0))
    return {
        "status": "blocked" if blockers > 0 else "ready",
        "source": "trace_compatibility",
        "cutover_blocker_count": blockers,
    }


def _recommendations(
    status: str,
    matrix: dict[str, Any],
    dual: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> list[str]:
    recs: list[str] = []
    recs.append("safe for simulation")

    matrix_mode = str(matrix.get("decision", {}).get("recommended_mode", "trace"))
    if matrix_mode in {"canary", "authoritative"} and status != "blocked":
        recs.append("safe for canary")
    if matrix_mode == "authoritative" and status != "blocked":
        recs.append("safe for authoritative testing")

    if status == "blocked":
        recs.append("not safe for default cutover")
    elif blockers:
        recs.append("conditionally cutover-ready")
    elif dual.get("status") == "warning" or matrix.get("status") == "warning":
        recs.append("conditionally cutover-ready")
    else:
        recs.append("not safe for default cutover")
    return recs


def _warnings(
    matrix: dict[str, Any],
    dual: dict[str, Any],
    dep_inventory: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> list[str]:
    if blockers:
        return []
    warns: list[str] = []
    warns.extend(str(item) for item in matrix.get("warnings", []))
    warns.extend(str(item) for item in dual.get("warnings", []))

    retained_count = len(dep_inventory.get("retained", []))
    if retained_count > 0:
        warns.append("compatibility_retained")
    candidate_count = len(dep_inventory.get("candidates", []))
    if candidate_count > 0:
        warns.append("future_deprecation_candidates")
    return sorted(dict.fromkeys(warns))


def _rollback_payload(matrix: dict[str, Any], dual: dict[str, Any]) -> dict[str, Any]:
    from_matrix = dict(matrix.get("matrix", {}).get("rollback", {}))
    from_dual = dict(dual.get("validation", {}).get("rollback", {}))
    payload = from_matrix or from_dual
    commands = list(payload.get("commands", []))
    payload["commands"] = commands
    payload["supported"] = bool(payload.get("supported", False))
    payload["method"] = payload.get("method", "env_unset")
    return payload


def _single_simulation(target: Path, *, deprecation_inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = evaluate_ledger_authority_readiness(target)
    dual = evaluate_dual_authority_validation(target)
    compatibility = summarize_trace_dependencies(matrix.get("matrix", {}).get("compatibility", {}))
    dep_inventory = deprecation_inventory if deprecation_inventory is not None else build_trace_deprecation_inventory()
    control_plane = _control_plane_status(compatibility)

    validation = {
        "authority_matrix": matrix,
        "dual_validation": dual,
        "compatibility": compatibility,
        "deprecation_inventory": {
            "status": dep_inventory.get("status", "informational"),
            "summary": dict(dep_inventory.get("summary", {})),
            "candidate_count": len(dep_inventory.get("candidates", [])),
            "retained_count": len(dep_inventory.get("retained", [])),
            "operational_count": len(dep_inventory.get("operational", [])),
        },
        "drift": dict(matrix.get("matrix", {}).get("drift", {})),
        "corruption": dict(matrix.get("matrix", {}).get("corruption", {})),
        "replay": dict(matrix.get("matrix", {}).get("replay", {})),
        "evals": dict(matrix.get("matrix", {}).get("evals", {})),
        "registry": dict(matrix.get("matrix", {}).get("registry", {})),
        "control_plane": control_plane,
    }

    simulation = _build_simulation_payload()
    rollback = _rollback_payload(matrix, dual)

    report = {
        "status": "ready",
        "simulation": simulation,
        "validation": validation,
        "blockers": [],
        "warnings": [],
        "recommendations": [],
        "rollback": rollback,
        "generated_at": _now_iso(),
    }
    blockers = default_authority_simulation_blockers(report)
    status = "blocked" if blockers else "ready"
    if not blockers and (matrix.get("status") == "warning" or dual.get("status") == "warning"):
        status = "warning"
    warnings = _warnings(matrix, dual, dep_inventory, blockers)
    if warnings and status == "ready":
        status = "warning"
    report["status"] = status
    report["blockers"] = blockers
    report["warnings"] = warnings
    report["recommendations"] = _recommendations(status, matrix, dual, blockers)
    return report


def _aggregate_simulation(runs_root: Path, recent: int | None = None) -> dict[str, Any]:
    runs = _run_dirs(runs_root, recent=recent)
    statuses: dict[str, int] = {"ready": 0, "warning": 0, "blocked": 0}
    warnings: set[str] = set()
    blocker_rows: list[dict[str, Any]] = []
    sample: dict[str, Any] | None = None

    shared_inventory = build_trace_deprecation_inventory()

    for run in runs:
        result = _single_simulation(run, deprecation_inventory=shared_inventory)
        statuses[result["status"]] = statuses.get(result["status"], 0) + 1
        warnings.update(str(item) for item in result.get("warnings", []))
        for item in result.get("blockers", []):
            tagged = dict(item)
            tagged["run"] = run.name
            blocker_rows.append(tagged)
        if sample is None:
            sample = result

    if sample is None:
        sample = {
            "simulation": _build_simulation_payload(),
            "validation": {},
            "rollback": {"supported": True, "method": "env_unset", "commands": []},
        }

    status = "blocked" if statuses["blocked"] else ("warning" if statuses["warning"] else "ready")
    blockers = sorted(
        blocker_rows,
        key=lambda item: (item.get("code", ""), item.get("area", ""), item.get("run", ""), item.get("message", "")),
    )
    recs = _recommendations(status, sample.get("validation", {}).get("authority_matrix", {}), sample.get("validation", {}).get("dual_validation", {}), blockers)

    return {
        "status": status,
        "simulation": dict(sample.get("simulation", {})),
        "validation": dict(sample.get("validation", {})),
        "blockers": blockers,
        "warnings": sorted(warnings),
        "recommendations": recs,
        "rollback": dict(sample.get("rollback", {})),
        "runs_scanned": len(runs),
        "generated_at": _now_iso(),
    }


def build_default_authority_simulation(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    root = Path(runs_root) if runs_root is not None else RUNS_DIR
    if recent is not None and recent < 0:
        raise ValueError("recent must be >= 0")

    if run_or_path is None:
        return _aggregate_simulation(root, recent=recent)

    target = _resolve_target(run_or_path, root)
    return _single_simulation(target)


def evaluate_default_authority_simulation(
    run_or_path: str | Path | None = None,
    *,
    runs_root: str | Path | None = None,
    recent: int | None = None,
) -> dict[str, Any]:
    return build_default_authority_simulation(run_or_path, runs_root=runs_root, recent=recent)


def default_authority_simulation_blockers(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    validation = simulation.get("validation", {})
    blockers: list[dict[str, Any]] = []

    if validation.get("drift", {}).get("detected"):
        blockers.append({"area": "drift", "code": "drift_detected", "message": "Trace/ledger drift detected"})
    if validation.get("corruption", {}).get("detected"):
        blockers.append({"area": "corruption", "code": "corruption_detected", "message": "Ledger corruption detected"})
    if validation.get("compatibility", {}).get("status") == "blocked":
        blockers.append({"area": "compatibility", "code": "compatibility_blockers", "message": "Trace compatibility blockers present"})
    if validation.get("replay", {}).get("status") == "blocked":
        blockers.append({"area": "replay", "code": "replay_not_ready", "message": "Replay is not ledger-ready"})
    if validation.get("evals", {}).get("status") == "blocked":
        blockers.append({"area": "evals", "code": "evals_not_ready", "message": "Evals are not ledger-ready"})
    if validation.get("registry", {}).get("status") == "blocked":
        blockers.append({"area": "registry", "code": "registry_not_ready", "message": "Registry is not ledger-ready"})
    if validation.get("control_plane", {}).get("status") == "blocked":
        blockers.append({"area": "control_plane", "code": "control_plane_incompatibility", "message": "Control-plane compatibility blockers detected"})
    if validation.get("authority_matrix", {}).get("status") == "blocked":
        blockers.append({"area": "authority_matrix", "code": "authority_matrix_blocked", "message": "Authority readiness matrix is blocked"})
    if validation.get("dual_validation", {}).get("status") == "blocked":
        blockers.append({"area": "dual_validation", "code": "dual_validation_blocked", "message": "Dual-authority validation is blocked"})

    if not bool(simulation.get("rollback", {}).get("supported", False)):
        blockers.append({"area": "rollback", "code": "rollback_missing", "message": "Rollback capability not available"})

    return sorted(blockers, key=lambda item: (item.get("code", ""), item.get("area", ""), item.get("message", "")))
