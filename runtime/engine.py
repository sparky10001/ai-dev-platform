#!/usr/bin/env python3
###################################################################
# runtime/engine.py — Thin Runtime Coordinator (Phase 3.5)
#
# Responsibilities:
# ✅ CLI argument parsing and command coordination
# ✅ adapter path/model selection coordination
# ✅ lifecycle orchestration via runtime.run_lifecycle
# ✅ adapter execution via runtime.adapter_gateway
# ✅ trace ingestion coordination via runtime.trace_pipeline
# ✅ deterministic final JSON response emission
# ✅ preservation of runtime contracts and replay semantics
#
# Explicitly delegated:
# - adapter subprocess execution → runtime.adapter_gateway
# - adapter response validation → runtime.adapter_gateway
# - run lifecycle transitions → runtime.run_lifecycle
# - NDJSON append/ingestion → runtime.trace_pipeline
# - replay loading → runtime.replay / runtime.trace_pipeline
#
###################################################################

from __future__ import annotations

import os
import sys

from pathlib import Path

from runtime.run_lifecycle import (
    build_response,
    initialize_run,
    start_run,
    record_agent_output,
    finalize_run as finalize_lifecycle_run,
    fail_run as lifecycle_fail_run,
)

from runtime.adapter_gateway import invoke_adapter
from runtime.trace_pipeline import ingest_trace_events

from runtime.validator import validate_response

from runtime.schemas import (
    ResponseModel,
)

# ================================================================
# 📁 Paths
# ================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

ADAPTERS_DIR = ROOT_DIR / "scripts" / "adapters"

# ================================================================
# 🧠 Model Routing
# ================================================================

def map_command_to_model(command: str) -> str:

    if command == "query":
        return "fast"

    if command in ("run", "fix", "refactor"):
        return "heavy"

    return "balanced"

# ================================================================
# 📦 Canonical Error Envelope
# ================================================================

def build_error(
    message: str,
    *,
    run_id: str | None = None,
    run_path: str | None = None,
) -> ResponseModel:

    return build_response(
        message,
        status="error",
        run_id=run_id,
        run_path=run_path,
        adapter="engine.py",
        error=True,
    )

# ================================================================
# 🏁 Failure Handling
# ================================================================

def fail_run(
    run,
    message: str,
    exit_code: int = 1,
):

    result = lifecycle_fail_run(run, message)

    print(
        result.model_dump_json(),
        flush=True
    )

    sys.exit(exit_code)

# ================================================================
# 🚀 Main
# ================================================================

def main():

    args = sys.argv[1:]

    if not args:

        print(
            build_error("Usage: ai <command> [args] - missing command")
            .model_dump_json()
        )

        sys.exit(1)

    command = args[0]

    remaining = args[1:]

    trace_enabled = (
        "--trace" in remaining
        or os.getenv("AI_TRACE") == "1"
    )

    model_override = None

    input_parts = []

    for arg in remaining:

        if arg == "--trace":
            continue

        elif arg.startswith("--model="):
            model_override = arg.split("=", 1)[1]

        else:
            input_parts.append(arg)

    user_input = " ".join(input_parts)

    model = (
        model_override
        or map_command_to_model(command)
    )

    # ============================================================
    # 🧾 Create Run
    # ============================================================

    run = initialize_run(
        task=user_input,
        command=command,
        model=model,
    )

    trace_path = Path(run["trace_path"])

    trace_path.touch(exist_ok=True)

    # ------------------------------------------------------------
    # Emit trace path immediately
    # ------------------------------------------------------------

    if trace_enabled:

        print(
            f"📋 Trace: {trace_path}",
            file=sys.stderr,
            flush=True,
        )

    # ============================================================
    # 📡 Session Start
    # ============================================================

    start_run(
        run=run,
        command=command,
        user_input=user_input,
        model=model,
    )

    # ============================================================
    # 🔌 Resolve Adapter
    # ============================================================

    adapter_name = os.getenv(
        "AI_ADAPTER",
        "agent"
    )

    adapter = (
        ADAPTERS_DIR /
        f"{adapter_name}.sh"
    )

    if not adapter.exists():

        fail_run(
            run,
            f"Adapter not found: {adapter_name}"
        )

    # ============================================================
    # 🚀 Execute Adapter
    # ============================================================

    try:

        validated_payload = invoke_adapter(
            command=[
                str(adapter),
                command,
                user_input,
                f"--model={model}",
            ],
            timeout=int(os.getenv("AI_TIMEOUT", "120")),
            env={
                "AI_RUN_ID": run["id"],
                "AI_RUN_PATH": run["run_path"],
                "AI_TRACE_PATH": run["trace_path"],
            },
        )

        validated_response = validate_response(validated_payload)

    except ValueError as e:

        fail_run(
            run,
            str(e)
        )

    # ============================================================
    # 📡 Trace Ingestion
    # ============================================================

    trace = (
        validated_response.meta.trace
        if validated_response.meta
        else []
    )

    ingest_trace_events(
        trace_path=trace_path,
        events=trace,
    )

    # ============================================================
    # 📦 Final Agent Output Event
    # ============================================================

    record_agent_output(
        run=run,
        status=validated_response.status,
        output=validated_response.output,
    )

    # ============================================================
    # 💾 Finalize Run
    # ============================================================

    finalize_lifecycle_run(
        run=run,
        status=validated_response.status,
        result=validated_response.model_dump(
            mode="json"
        ),
    )

    # ============================================================
    # 📤 Emit Final Response
    # ============================================================

    print(
        validated_response.model_dump_json(),
        flush=True
    )

# ================================================================
# 🏁 Entrypoint
# ================================================================

if __name__ == "__main__":
    main()