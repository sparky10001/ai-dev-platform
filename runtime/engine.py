#!/usr/bin/env python3
###################################################################
# runtime/engine.py — Runtime Engine (Phase 3)
#
# Responsibilities:
# ✅ canonical run lifecycle
# ✅ schema-validated adapter responses
# ✅ NDJSON event durability
# ✅ replay-safe event ingestion
# ✅ deterministic runtime envelopes
# ✅ trace persistence
# ✅ adapter orchestration
# ✅ schema-versioned runtime contracts
#
###################################################################

from __future__ import annotations

import json
import os
import sys

from pathlib import Path

from runtime.run import create_run
from runtime.run import finalize_run

from runtime.events import log_event

from runtime.adapter_gateway import invoke_adapter

from runtime.validator import (
    validate_response,
    validate_event,
)

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

    return validate_response({
        "status": "error",
        "output": message,
        "meta": {
            "adapter": "engine.py",
            "error": True,
            "run_id": run_id or "no_run",
            "run_path": run_path or "",
        }
    })

# ================================================================
# 🏁 Failure Handling
# ================================================================

def fail_run(
    run,
    message: str,
    exit_code: int = 1,
):

    result = build_error(
        message,
        run_id=run["id"],
        run_path=run["run_path"],
    )

    try:

        log_event(
            run,
            "agent_output",
            {
                "status": "error",
                "output": message,
            }
        )

        log_event(
            run,
            "session_end",
            {
                "status": "error",
            }
        )

    except Exception:
        pass

    try:
        finalize_run(
            run,
            result.model_dump(mode="json")
        )
    except Exception:
        pass

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

    run = create_run(
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

    log_event(
        run,
        "session_start",
        {
            "command": command,
            "input": user_input,
            "model": model,
        }
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

    if isinstance(trace, list):

        for evt in trace:

            try:

                validated_evt = validate_event(evt)

                with open(trace_path, "a", encoding="utf-8") as f:
                    json.dump(
                        validated_evt.model_dump(mode="json"),
                        f,
                    )
                    f.write("\n")

            except Exception:
                continue

    # ============================================================
    # 📦 Final Agent Output Event
    # ============================================================

    log_event(
        run,
        "agent_output",
        {
            "status": validated_response.status,
            "output": validated_response.output,
        }
    )

    # ============================================================
    # 🏁 Session End
    # ============================================================

    log_event(
        run,
        "session_end",
        {
            "status": validated_response.status,
        }
    )

    # ============================================================
    # 💾 Finalize Run
    # ============================================================

    finalize_run(
        run,
        validated_response.model_dump(
            mode="json"
        )
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