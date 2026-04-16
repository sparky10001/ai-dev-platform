import os

name = "read_file"
description = "Read a file from the workspace"

def run(input_data):
    path = input_data.get("path")

    if not path:
        return {
            "status": "error",
            "output": "Missing 'path'"
        }

    if not os.path.exists(path):
        return {
            "status": "error",
            "output": f"File not found: {path}"
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
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