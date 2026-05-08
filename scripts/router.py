#!/usr/bin/env python3
###################################################################
# router.py — Deterministic Planner (v6.1)
###################################################################

import re
import json


def match_write_file(text):

    name = re.search(
        r"file called ([\w\.\-\/]+)",
        text,
        re.IGNORECASE
    )

    content = re.search(
        r"content ['\"](.+?)['\"]",
        text,
        re.IGNORECASE
    )

    if not name:
        return None

    return {
        "tool": "write_file",
        "args": {
            "path": name.group(1),
            "content": content.group(1) if content else "",
            "overwrite": True
        },
        "save_as": "file"
    }


def match_list_files(text):

    if re.search(r"list files|show files", text, re.IGNORECASE):
        return {
            "tool": "list_files",
            "args": {
                "path": "."
            },
            "save_as": "files"
        }

    return None


def match_read_file(text):

    m = re.search(
        r"read (?:file )?([\w\.\-\/]+)",
        text,
        re.IGNORECASE
    )

    if not m:
        return None

    return {
        "tool": "read_file",
        "args": {
            "path": m.group(1)
        },
        "save_as": "content"
    }


def match_say(text):

    m = re.search(
        r"say (.+)",
        text,
        re.IGNORECASE
    )

    if not m:
        return None

    return {
        "tool": "run_bash",
        "args": {
            "command": f"echo {json.dumps(m.group(1))}"
        },
        "save_as": "response"
    }


MATCHERS = [
    match_write_file,
    match_list_files,
    match_read_file,
    match_say
]


def build_plan(user_input):

    steps = []

    for matcher in MATCHERS:

        result = matcher(user_input)

        if result:
            steps.append(result)

    return steps


def route(user_input):

    normalized = user_input.strip().lower()

    # 🩺 Healthcheck route
    if normalized == "ping":
        return {
            "mode": "healthcheck",
            "plan": []
        }

    plan = build_plan(user_input)

    if not plan:
        return None

    return {
        "mode": "deterministic",
        "plan": plan
    }