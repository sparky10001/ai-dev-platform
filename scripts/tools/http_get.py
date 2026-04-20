###################################################################
# http_get.py — HTTP GET request tool (v1.2 production)
#
# Safety features:
# - Localhost/private IP blocking (optional)
# - Configurable timeout
# - Response size limit
# - Header support
# - JSON auto-detection
###################################################################

import json
import urllib.request
import urllib.error
import urllib.parse
import socket

name = "http_get"
description = "Make an HTTP GET request to a URL and return the response"
input_schema = {
    "url": "string (required) — URL to fetch",
    "timeout": "int (optional, default 10) — max seconds",
    "headers": "dict (optional) — request headers",
    "max_bytes": "int (optional, default 65536) — max response size",
    "allow_private": "bool (optional, default false) — allow private/localhost IPs"
}

MAX_BYTES_DEFAULT = 65536  # 64KB
PRIVATE_RANGES = [
    "localhost",
    "127.",
    "192.168.",
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "::1"
]


def is_private_url(url):
    """Check if URL resolves to a private/localhost address."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        return any(host.startswith(r) or host == r for r in PRIVATE_RANGES)
    except Exception:
        return False


def run(input_data):
    url = input_data.get("url")
    timeout = input_data.get("timeout", 10)
    headers = input_data.get("headers", {})
    max_bytes = input_data.get("max_bytes", MAX_BYTES_DEFAULT)
    allow_private = input_data.get("allow_private", True)  # default allow for dev use

    # ---- Validate ----
    if not url:
        return {"status": "error", "output": "Missing 'url'"}

    if not isinstance(url, str):
        return {"status": "error", "output": "'url' must be a string"}

    if not url.startswith(("http://", "https://")):
        return {"status": "error", "output": "URL must start with http:// or https://"}

    # ---- Private IP check ----
    if not allow_private and is_private_url(url):
        return {
            "status": "error",
            "output": f"Private/localhost URLs blocked. Set allow_private=true to override."
        }

    # ---- Build request ----
    try:
        req = urllib.request.Request(url)

        # Default headers
        req.add_header("User-Agent", "ai-dev-platform/1.0")

        # Custom headers
        if isinstance(headers, dict):
            for key, val in headers.items():
                req.add_header(key, str(val))

        # ---- Execute ----
        with urllib.request.urlopen(req, timeout=int(timeout)) as response:
            status_code = response.status
            content_type = response.headers.get("Content-Type", "")

            raw = response.read(int(max_bytes))
            body = raw.decode("utf-8", errors="replace")

            # ---- Auto-detect JSON ----
            parsed = None
            if "application/json" in content_type:
                try:
                    parsed = json.loads(body)
                except Exception:
                    pass

            return {
                "status": "done",
                "output": parsed if parsed is not None else body,
                "status_code": status_code,
                "content_type": content_type,
                "bytes_read": len(raw)
            }

    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(4096).decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "status": "error",
            "output": f"HTTP {e.code}: {e.reason}",
            "status_code": e.code,
            "body": body
        }

    except urllib.error.URLError as e:
        return {"status": "error", "output": f"URL error: {str(e.reason)}"}

    except socket.timeout:
        return {"status": "error", "output": f"Request timed out after {timeout}s"}

    except Exception as e:
        return {"status": "error", "output": f"Request failed: {str(e)}"}
