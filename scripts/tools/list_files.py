import os

name = "list_files"
description = "List files in a directory within the workspace"

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
            "output": f"Path not found: {rel_path}"
        }

    if not os.path.isdir(full_path):
        return {
            "status": "error",
            "output": f"Not a directory: {rel_path}"
        }

    try:
        entries = []

        for name_ in os.listdir(full_path):
            entry_path = os.path.join(full_path, name_)
            entries.append({
                "name": name_,
                "type": "dir" if os.path.isdir(entry_path) else "file"
            })

        return {
            "status": "done",
            "output": entries
        }

    except Exception as e:
        return {
            "status": "error",
            "output": str(e)
        }