#!/usr/bin/env python3
###################################################################
# agent.py — Agent Runtime (v9.1 PHASE 3E STABLE)
#
# ✅ Preserves external JSON contract
# ✅ Preserves evaluator compatibility
# ✅ Preserves legacy trace schema
# ✅ Uses Pydantic v2 response validation
# ✅ Uses NDJSON runtime event persistence
# ✅ Avoids nested schema_version drift
# ✅ Keeps schema_version ownership at envelope/event layers
# ✅ Compatible with runtime/replay.py
# ✅ Compatible with runtime/validator.py
# ✅ Compatible with runtime/events.py
###################################################################

import os
import sys
import json
import time
import subprocess

from pathlib import Path

from router import route
from lib.trace_logger import TraceLogger

from runtime.validator import validate_response
from runtime.events import log_event

# ================================================================
# ⚙️ CONFIG
# ================================================================

SCHEMA_VERSION = 1

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

TOOL_EXECUTOR = SCRIPT_DIR / "tool_executor.py"

MAX_STEPS = int(
    os.getenv("AI_MAX_STEPS", "6")
)

# ================================================================
# 📁 LOGGING DIRECTORIES
# ================================================================

RUNS_DIR = Path(
    os.getenv(
        "AI_RUNS_DIR",
        ROOT_DIR / "runs"
    )
)

TRACE_DIR = Path(
    os.getenv(
        "AI_TRACE_DIR",
        ROOT_DIR / "logs" / "traces"
    )
)

EVAL_DIR = Path(
    os.getenv(
        "AI_EVAL_DIR",
        ROOT_DIR / "logs" / "evals"
    )
)

RUNS_DIR.mkdir(parents=True, exist_ok=True)
TRACE_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# ================================================================
# 🧾 RUN CONTEXT
# ================================================================

RUN_ID = f"run_{int(time.time() * 1000)}"

RUN_PATH = RUNS_DIR / RUN_ID
RUN_PATH.mkdir(parents=True, exist_ok=True)

TRACE_JSON_PATH = RUN_PATH / "trace.json"
TRACE_NDJSON_PATH = RUN_PATH / "trace.jsonl"
RESULT_JSON_PATH = RUN_PATH / "result.json"

# ================================================================
# 🧠 RUNTIME RUN OBJECT
# ================================================================

RUN = {
    "id": RUN_ID,
    "path": str(RUN_PATH),
    "trace_path": str(TRACE_NDJSON_PATH),
}

# ================================================================
# 🔍 TRACE LOGGER
# ================================================================

trace_logger = TraceLogger()

# ================================================================
# 🧠 MEMORY RESOLUTION
# ================================================================

def resolve_value(expr, memory, last):

    if not isinstance(expr, str):
        return expr

    if expr.startswith("$"):

        parts = expr[1:].split(".")
        var = parts[0]

        if var in memory:
            val = memory[var]

        elif var == "last":
            val = last

        else:
            return None

        for p in parts[1:]:

            if isinstance(val, dict):
                val = val.get(p)
            else:
                return None

        return val

    return expr


def resolve_args(args, memory, last):

    if not isinstance(args, dict):
        return args

    return {
        k: resolve_value(v, memory, last)
        for k, v in args.items()
    }

# ================================================================
# 🧠 CONDITIONS
# ================================================================

def eval_condition(expr, memory, last):

    if not expr:
        return True

    try:

        ctx = {
            "last": last,
            **memory
        }

        return bool(eval(expr, {}, ctx))

    except Exception:
        return False

# ================================================================
# 🧾 RESPONSE HELPERS
# ================================================================

def runtime_meta(extra=None):

    return {
        "adapter": "agent.py",
        "run_id": RUN_ID,
        "run_path": str(RUN_PATH),
        "error": False,
        **(extra or {})
    }


def respond(status, output, meta=None):

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "output": output,
        "meta": runtime_meta(meta)
    }


def done(output, meta=None):

    return respond(
        "done",
        output,
        meta
    )


def error(msg):

    return respond(
        "error",
        msg,
        {
            "error": True
        }
    )


def with_trace(meta, trace_events):

    meta = meta or {}

    meta["trace"] = trace_events

    return meta

# ================================================================
# 🧰 TOOL DISCOVERY
# ================================================================

def load_tools():

    try:

        proc = subprocess.run(
            [
                "python3",
                str(TOOL_EXECUTOR),
                "--list-tools-openai"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if proc.returncode != 0:
            return None

        raw = (proc.stdout or "").strip()

        start = raw.find("{")

        if start == -1:
            return None

        raw = raw[start:]

        data = json.loads(raw)

        tools = data.get("tools")

        if not isinstance(tools, list):
            return None

        return tools

    except Exception as e:

        print(
            f"load_tools failed: {e}",
            file=sys.stderr
        )

        return None

# ================================================================
# 🔌 TOOL EXECUTION
# ================================================================

def run_tool(name, args):

    try:

        proc = subprocess.run(
            [
                "python3",
                str(TOOL_EXECUTOR),
                name,
                json.dumps(args)
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if proc.returncode != 0:

            return {
                "status": "error",
                "error": {
                    "message": proc.stderr.strip()
                }
            }

        return json.loads(proc.stdout)

    except Exception as e:

        return {
            "status": "error",
            "error": {
                "message": str(e)
            }
        }

# ================================================================
# 💾 RUN LOGGING
# ================================================================

def write_run_logs(final_result, trace_events):

    try:

        with open(
            TRACE_JSON_PATH,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                trace_events,
                f,
                indent=2
            )

        with open(
            RESULT_JSON_PATH,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                final_result,
                f,
                indent=2
            )

        eval_record = {
            "run_id": RUN_ID,
            "timestamp": int(time.time()),
            "status": final_result.get("status"),
            "output": final_result.get("output"),
            "steps": (
                final_result
                .get("meta", {})
                .get("steps", 0)
            )
        }

        eval_path = (
            EVAL_DIR /
            f"eval.{RUN_ID}.json"
        )

        with open(
            eval_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                eval_record,
                f,
                indent=2
            )

    except Exception as e:

        print(
            f"⚠️ Failed writing logs: {e}",
            file=sys.stderr
        )

# ================================================================
# 🤖 AGENT LOOP
# ================================================================

def run_agent(command, user_input, model=None):

    trace_events = []

    # ============================================================
    # SESSION START
    # ============================================================

    log_event(
        RUN,
        "session_start",
        {
            "command": command,
            "input": user_input,
            "model": model,
        }
    )

    # ------------------------------------------------------------
    # Tool Discovery
    # ------------------------------------------------------------

    tools = load_tools()

    if not tools:

        result = error("No tools available")

        log_event(
            RUN,
            "agent_output",
            result
        )

        log_event(
            RUN,
            "session_end",
            {
                "status": "error"
            }
        )

        return result

    # ------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------

    routing = route(user_input)

    # ------------------------------------------------------------
    # Healthcheck
    # ------------------------------------------------------------

    if (
        routing and
        routing.get("mode") == "healthcheck"
    ):

        result = done(
            "pong",
            with_trace(
                {
                    "mode": "healthcheck",
                    "steps": 0
                },
                trace_events
            )
        )

        log_event(
            RUN,
            "agent_output",
            result
        )

        log_event(
            RUN,
            "session_end",
            {
                "status": "done"
            }
        )

        return result

    # ------------------------------------------------------------
    # No route
    # ------------------------------------------------------------

    if not routing:

        result = respond(
            "error",
            "No deterministic plan available",
            with_trace(
                {
                    "error": True
                },
                trace_events
            )
        )

        log_event(
            RUN,
            "agent_output",
            result
        )

        log_event(
            RUN,
            "session_end",
            {
                "status": "error"
            }
        )

        return result

    # ------------------------------------------------------------
    # Runtime State
    # ------------------------------------------------------------

    memory = {}

    last_result = None
    last_tool = None

    step_counter = 0

    # ------------------------------------------------------------
    # Execute Plan
    # ------------------------------------------------------------

    for step in routing["plan"]:

        if step_counter >= MAX_STEPS:
            return error("Max steps exceeded")

        tool_name = step["tool"]

        if tool_name == last_tool:
            return error(
                f"Tool loop detected: {tool_name}"
            )

        cond = step.get("when")

        if not eval_condition(
            cond,
            memory,
            last_result
        ):
            continue

        args = resolve_args(
            step.get("args", {}),
            memory,
            last_result
        )

        step_counter += 1

        # ========================================================
        # LEGACY TRACE EVENT
        # ========================================================

        tool_call_event = {
            "event": "tool_call",
            "step": step_counter,
            "data": tool_name,
            "meta": {
                "input": args
            }
        }

        trace_events.append(tool_call_event)

        # ========================================================
        # NDJSON EVENT
        # ========================================================

        log_event(
            RUN,
            "tool_call",
            tool_name,
            step=step_counter,
            meta={
                "input": args
            }
        )

        trace_logger.emit(
            "tool_call",
            tool_name,
            {
                "step": step_counter,
                "input": args,
                "run_id": RUN_ID
            }
        )

        # --------------------------------------------------------
        # Run Tool
        # --------------------------------------------------------

        result = run_tool(
            tool_name,
            args
        )

        tool_result_event = {
            "event": "tool_result",
            "step": step_counter,
            "data": tool_name,
            "meta": {
                "result": result
            }
        }

        trace_events.append(
            tool_result_event
        )

        # ========================================================
        # NDJSON EVENT
        # ========================================================

        log_event(
            RUN,
            "tool_result",
            tool_name,
            step=step_counter,
            meta={
                "result": result
            }
        )

        trace_logger.emit(
            "tool_result",
            tool_name,
            {
                "step": step_counter,
                "result": result,
                "run_id": RUN_ID
            }
        )

        # --------------------------------------------------------
        # Memory Save
        # --------------------------------------------------------

        save_as = step.get("save_as")

        if (
            save_as and
            result.get("status") == "success"
        ):
            memory[save_as] = result

        last_result = result
        last_tool = tool_name

    # ============================================================
    # FINAL RESPONSE
    # ============================================================

    final_result = done(
        "completed_with_tools",
        with_trace(
            {
                "mode": "deterministic",
                "steps": step_counter,
                "memory": memory,
                "run_id": RUN_ID,
                "run_path": str(RUN_PATH)
            },
            trace_events
        )
    )

    # ============================================================
    # VALIDATE RESPONSE
    # ============================================================

    validated = validate_response(
        final_result
    )

    final_result = validated.model_dump()

    # ============================================================
    # WRITE LOGS
    # ============================================================

    write_run_logs(
        final_result,
        trace_events
    )

    # ============================================================
    # PERSIST OUTPUT EVENT
    # ============================================================

    log_event(
        RUN,
        "agent_output",
        final_result
    )

    log_event(
        RUN,
        "session_end",
        {
            "status": final_result["status"]
        }
    )

    trace_logger.emit(
        "agent_complete",
        "completed_with_tools",
        {
            "steps": step_counter,
            "run_id": RUN_ID
        }
    )

    return final_result

# ================================================================
# 🚀 ENTRYPOINT
# ================================================================

def main():

    args = sys.argv[1:]

    if not args:

        result = error("Missing command")

        validated = validate_response(result)

        print(
            validated.model_dump_json()
        )

        return

    command = args[0]

    user_input = (
        args[1]
        if len(args) > 1
        else ""
    )

    model = None

    for a in args:

        if a.startswith("--model="):
            model = a.split("=", 1)[1]

    result = run_agent(
        command,
        user_input,
        model
    )

    validated = validate_response(
        result
    )

    print(
        validated.model_dump_json()
    )

# ================================================================
# 🏁 MAIN
# ================================================================

if __name__ == "__main__":
    main()