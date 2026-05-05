#!/usr/bin/env python3
###################################################################
# router.py — Deterministic Tool Router (v1.0 production)
#
# Purpose:
# - Detect simple + multi-step tool tasks
# - Build execution plan
# - Execute without LLM
# - Return trace-compatible output
###################################################################

import re

# ================================================================
# 🎯 ROUTING RULES
# ================================================================
def match_write_file(text):
    name = re.search(r"file called ([\w\.\-\/]+)", text)
    content = re.search(r"content ['\"](.+?)['\"]", text)

    if name:
        return {
            "tool": "write_file",
            "args": {
                "path": name.group(1),
                "content": content.group(1) if content else ""
            }
        }

    return None


def match_list_files(text):
    if "list files" in text or "show files" in text:
        return {
            "tool": "list_files",
            "args": {"path": "."}
        }
    return None


def match_read_file(text):
    name = re.search(r"read (file )?([\w\.\-\/]+)", text)
    if name:
        return {
            "tool": "read_file",
            "args": {"path": name.group(2)}
        }
    return None


def match_run_bash(text):
    cmd = re.search(r"run (.+)", text)
    if cmd:
        return {
            "tool": "run_bash",
            "args": {"command": cmd.group(1)}
        }
    return None


# ================================================================
# 🧠 PLAN BUILDER
# ================================================================
def build_plan(user_input):
    text = user_input.lower()

    steps = []

    # ORDER MATTERS (multi-step support)
    for matcher in [
        match_write_file,
        match_list_files,
        match_read_file,
        match_run_bash,
    ]:
        step = matcher(text)
        if step:
            steps.append(step)

    return steps if steps else None


# ================================================================
# 🔍 CONFIDENCE CHECK
# ================================================================
def is_confident(plan):
    if not plan:
        return False

    # Simple heuristic:
    # if we detected at least one valid tool → high confidence
    return len(plan) > 0


# ================================================================
# 🚀 ENTRYPOINT
# ================================================================
def route(user_input):
    plan = build_plan(user_input)

    if not is_confident(plan):
        return None

    return {
        "mode": "deterministic",
        "plan": plan
    }