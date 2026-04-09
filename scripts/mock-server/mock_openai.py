###################################################################
# mock_openai.py — Minimal OpenAI-compatible mock server
#
# Purpose:
#   Validate that Goose → API call chain works correctly
#   without requiring a real AI provider
#
# Usage:
#   uvicorn mock_openai:app --host 0.0.0.0 --port 8000
#
# Test:
#   curl http://localhost:8000/health
#   curl http://localhost:8000/v1/models
#   curl http://localhost:8000/v1/chat/completions \
#     -H "Content-Type: application/json" \
#     -d '{"model":"mock-model","messages":[{"role":"user","content":"hello"}]}'
###################################################################

import json
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Mock OpenAI Server", version="1.0.0")


# ---- Models ----

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list
    temperature: float = 0.7
    max_tokens: int = 100
    stream: bool = False


# ---- Health ----

@app.get("/health")
def health():
    return {
        "status": "ok",
        "server": "mock-openai",
        "version": "1.0.0"
    }


# ---- Models endpoint ----

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "mock-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "mock"
            }
        ]
    }


# ---- Chat completions ----

@app.post("/v1/chat/completions")
async def chat(req: ChatRequest, request: Request):

    # Extract last user message
    user_msg = ""
    for msg in reversed(req.messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    # Debug info — echoes full request context
    debug_info = {
        "model": req.model,
        "message_count": len(req.messages),
        "temperature": req.temperature,
        "last_user_message": user_msg,
        "all_roles": [m.get("role") for m in req.messages]
    }

    # Mock response content
    content = (
        f"[MOCK SERVER] Received: {user_msg}\n"
        f"Debug: {json.dumps(debug_info, indent=2)}"
    )

    return {
        "id": f"mock-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
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
            "completion_tokens": 20,
            "total_tokens": len(user_msg.split()) + 20
        }
    }


# ---- Catch-all for debugging unknown routes ----

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path: str, request: Request):
    body = await request.body()
    return JSONResponse(
        status_code=404,
        content={
            "error": f"Route not found: /{path}",
            "method": request.method,
            "body": body.decode() if body else None,
            "hint": "Available routes: /health, /v1/models, /v1/chat/completions"
        }
    )
