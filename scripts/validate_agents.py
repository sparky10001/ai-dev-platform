#!/usr/bin/env python3

import os
import sys
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.path.join(ROOT, "agents")

REQUIRED_FIELDS = ["name", "mission"]

def fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def validate_file(path):
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        fail(f"{os.path.basename(path)}: YAML parse error → {e}")

    if not isinstance(data, dict):
        fail(f"{os.path.basename(path)}: must be a YAML object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            fail(f"{os.path.basename(path)}: missing '{field}'")

    if "rules" in data and not isinstance(data["rules"], list):
        fail(f"{os.path.basename(path)}: rules must be a list")

    if "process" in data and not isinstance(data["process"], list):
        fail(f"{os.path.basename(path)}: process must be a list")

    if "style" in data and not isinstance(data["style"], dict):
        fail(f"{os.path.basename(path)}: style must be an object")

    print(f"✅ {os.path.basename(path)}")

def main():
    if not os.path.isdir(AGENTS_DIR):
        fail("agents/ directory not found")

    files = [f for f in os.listdir(AGENTS_DIR) if f.endswith(".yaml")]

    if not files:
        fail("no agent specs found")

    for f in files:
        validate_file(os.path.join(AGENTS_DIR, f))

    print("🎉 All agents valid")

if __name__ == "__main__":
    main()