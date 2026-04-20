import os

name = "read_file"
description = "Read a file from the workspace"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def run(input_data):
    rel_path = input_data.get("path", "")

    # ---- Resolve safe path ----
    full_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))

    # 🔒 Prevent path traversal
    if not full_path.startswith(BASE_DIR):
        return {
            "status": "error",
            "output": "Access denied (path outside workspace)"
        }

    if not os.path.exists(full_path):
        return {
            "status": "error",
            "output": f"File not found: {rel_path}"
        }

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "status": "done",
            "output": content
        }

    except Exception as e:
        return {
            "status": "error",
            "output": str(e)
        }