#!/usr/bin/env python3
###################################################################
# mock_openai.py — OpenAI-compatible mock server (v2.0)
#
# Purpose:
#   - Validate full AI pipeline (LiteLLM → adapters → agent)
#   - Provide deterministic + debuggable responses
#   - Support streaming + failure injection
#
# Features:
#   - /health (liveness)
#   - /v1/models (OpenAI-compatible)
#   - /v1/chat/completions (standard + streaming)
#   - Latency + failure simulation via env
#
# Env Controls:
#   MOCK_DELAY_MS=0
#   MOCK_FAIL_RATE=0.0   (0.0–1.0)
#   MOCK_DEBUG=1
###################################################################

import json
import os
import time
import random
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# ================================================================
# ⚙️ Config
# ================================================================

MOCK_DELAY_MS = int(os.getenv("MOCK_DELAY_MS", "0"))
MOCK_FAIL_RATE = float(os.getenv("MOCK_FAIL_RATE", "0.0"))
MOCK_DEBUG = os.getenv("MOCK_DEBUG", "0") == "1"

APP_VERSION = "2.0.0"

app = FastAPI(title="Mock OpenAI Server", version=APP_VERSION)


# ================================================================
# 🧱 Models
# ================================================================

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 100
    stream: Optional[bool] = False


# ================================================================
# 🧰 Helpers
# ================================================================

def maybe_delay():
    if MOCK_DELAY_MS > 0:
        time.sleep(MOCK_DELAY_MS / 1000.0)


def maybe_fail():
    if MOCK_FAIL_RATE > 0 and random.random() < MOCK_FAIL_RATE:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Mock failure injected",
                    "type": "mock_error"
                }
            }
        )
    return None


def extract_last_user_message(messages: List[Message]) -> str:
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def debug_log(data):
    if MOCK_DEBUG:
        print(f"[MOCK DEBUG] {json.dumps(data, indent=2)}")


# ================================================================
# ❤️ Health
# ================================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mock-openai",
        "version": APP_VERSION,
        "timestamp": int(time.time())
    }


# ================================================================
# 📦 Models endpoint
# ================================================================

@app.get("/v1/models")
def list_models():
    now = int(time.time())

    return {
        "object": "list",
        "data": [
            {
                "id": "mock-fast",
                "object": "model",
                "created": now,
                "owned_by": "mock"
            },
            {
                "id": "mock-code",
                "object": "model",
                "created": now,
                "owned_by": "mock"
            }
        ]
    }


# ================================================================
# 💬 Chat completions
# ================================================================

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest, request: Request):

    # Failure injection
    failure = maybe_fail()
    if failure:
        return failure

    maybe_delay()

    user_msg = extract_last_user_message(req.messages)

    debug_info = {
        "model": req.model,
        "message_count": len(req.messages),
        "temperature": req.temperature,
        "stream": req.stream,
        "last_user_message": user_msg,
        "roles": [m.role for m in req.messages],
    }

    debug_log(debug_info)

    content = (
        f"[MOCK:{req.model}] {user_msg}\n"
        f"(messages={len(req.messages)}, temp={req.temperature})"
    )

    created = int(time.time())
    completion_id = f"mock-{created}"

    # ------------------------------------------------------------
    # 🔄 Streaming response (SSE)
    # ------------------------------------------------------------
    if req.stream:

        def event_stream():
            tokens = content.split()

            for i, token in enumerate(tokens):
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": token + " "
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                time.sleep(0.02)

            # Final chunk
            yield f"data: {json.dumps({'choices':[{'finish_reason':'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # ------------------------------------------------------------
    # 📦 Standard response
    # ------------------------------------------------------------
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_msg.split()),
            "completion_tokens": len(content.split()),
            "total_tokens": len(user_msg.split()) + len(content.split())
        }
    }


# ================================================================
# ❌ Catch-all (debugging)
# ================================================================

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path: str, request: Request):
    body = await request.body()

    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "message": f"Route not found: /{path}",
                "type": "invalid_request_error"
            },
            "method": request.method,
            "body": body.decode() if body else None,
            "hint": "Available: /health, /v1/models, /v1/chat/completions"
        }
    )