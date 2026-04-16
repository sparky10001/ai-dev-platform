import os

name = "write_file"
description = "Write a file within the workspace"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

def run(input_data):
    rel_path = input_data.get("path")
    content = input_data.get("content")
    overwrite = input_data.get("overwrite", True)

    if not rel_path:
        return {"status": "error", "output": "Missing 'path'"}

    if content is None:
        return {"status": "error", "output": "Missing 'content'"}

    # ---- Resolve safe path ----
    full_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))

    # 🔒 Prevent path traversal
    if not full_path.startswith(BASE_DIR):
        return {
            "status": "error",
            "output": "Access denied (path outside workspace)"
        }

    # ---- Prevent overwrite (optional safety) ----
    if os.path.exists(full_path) and not overwrite:
        return {
            "status": "error",
            "output": f"File exists (overwrite disabled): {rel_path}"
        }

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "done",
            "output": f"File written: {rel_path}"
        }

    except Exception as e:
        return {
            "status": "error",
            "output": str(e)
        }