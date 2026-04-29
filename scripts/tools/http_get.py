###################################################################
# http_get.py — HTTP GET request tool (MCP-compliant v2.0)
###################################################################

import json
import urllib.request
import urllib.error
import urllib.parse
import socket

name = "http_get"
description = "Fetch a URL via HTTP GET and return structured response"

input_schema = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "URL to fetch (http or https)"
        },
        "timeout": {
            "type": "integer",
            "description": "Request timeout in seconds",
            "default": 10
        },
        "headers": {
            "type": "object",
            "description": "Optional request headers",
            "additionalProperties": {
                "type": "string"
            }
        },
        "max_bytes": {
            "type": "integer",
            "description": "Maximum response size in bytes",
            "default": 65536
        },
        "allow_private": {
            "type": "boolean",
            "description": "Allow private/localhost requests",
            "default": False
        }
    },
    "required": ["url"]
}

MAX_BYTES_DEFAULT = 65536

PRIVATE_RANGES = [
    "localhost",
    "127.",
    "192.168.",
    "10.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "::1"
]

# ================================================================
# 🧱 RESPONSE HELPERS
# ================================================================

def success(data, meta=None):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "meta": meta or {}
    }

def failure(message, error_type="tool_error", meta=None):
    return {
        "status": "error",
        "data": None,
        "error": {
            "message": message,
            "type": error_type
        },
        "meta": meta or {}
    }

# ================================================================
# 🔐 SAFETY
# ================================================================

def is_private_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        return any(host.startswith(r) or host == r for r in PRIVATE_RANGES)
    except Exception:
        return False

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data):
    url = input_data.get("url")
    timeout = int(input_data.get("timeout", 10))
    headers = input_data.get("headers", {})
    max_bytes = int(input_data.get("max_bytes", MAX_BYTES_DEFAULT))
    allow_private = bool(input_data.get("allow_private", False))

    # ---- Validate ----
    if not isinstance(url, str) or not url:
        return failure("Invalid or missing 'url'", "validation_error")

    if not url.startswith(("http://", "https://")):
        return failure("URL must start with http:// or https://", "validation_error")

    if not allow_private and is_private_url(url):
        return failure(
            "Private/localhost URLs are blocked",
            "security_error"
        )

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ai-dev-platform/2.0")

        if isinstance(headers, dict):
            for k, v in headers.items():
                req.add_header(str(k), str(v))

        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.status
            content_type = response.headers.get("Content-Type", "")

            raw = response.read(max_bytes)

            # Safe decode
            body = raw.decode("utf-8", errors="replace")

            parsed_json = None
            if "application/json" in content_type:
                try:
                    parsed_json = json.loads(body)
                except Exception:
                    pass

            return success({
                "url": url,
                "status_code": status_code,
                "content_type": content_type,
                "bytes_read": len(raw),
                "body": parsed_json if parsed_json is not None else body
            })

    except urllib.error.HTTPError as e:
        try:
            body = e.read(4096).decode("utf-8", errors="replace")
        except Exception:
            body = ""

        return failure(
            f"HTTP {e.code}: {e.reason}",
            "http_error",
            meta={
                "status_code": e.code,
                "body": body
            }
        )

    except urllib.error.URLError as e:
        return failure(f"URL error: {str(e.reason)}", "network_error")

    except socket.timeout:
        return failure(f"Request timed out after {timeout}s", "timeout")

    except Exception as e:
        return failure(f"Request failed: {str(e)}", "execution_error")