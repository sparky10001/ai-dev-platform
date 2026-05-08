#!/usr/bin/env python3

import json
import os
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

TRACE_DIR = Path(
    os.getenv(
        "AI_TRACE_DIR",
        BASE_DIR / "logs" / "traces"
    )
)

TRACE_DIR.mkdir(parents=True, exist_ok=True)


class TraceLogger:
    def __init__(self):
        ts = int(time.time())
        pid = os.getpid()

        self.session_id = str(uuid.uuid4())

        self.path = TRACE_DIR / f"ai_trace.{ts}_{pid}.log"

    def emit(self, event, data=None, meta=None):
        payload = {
            "timestamp": time.time(),
            "session_id": self.session_id,
            "event": event,
            "data": data,
            "meta": meta or {}
        }

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")