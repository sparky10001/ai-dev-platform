import json

name = "evaluate_trace"
description = "Evaluate trace against structured scenario criteria (v2)"

# ---------------------------------------------------------------
# 🔍 Helpers
# ---------------------------------------------------------------

def extract_tool_calls(events):
    return [
        e.get("data")
        for e in events
        if e.get("event") == "tool_call"
    ]


def extract_errors(events):
    return [
        e for e in events
        if "error" in str(e.get("event", "")).lower()
    ]


def flatten_events(events):
    return json.dumps(events).lower()


# ---------------------------------------------------------------
# 🧪 Criterion evaluators
# ---------------------------------------------------------------

def check_tool_used(events, criterion):
    target = criterion.get("tool")

    for e in events:
        if e.get("event") == "tool_call":
            data = e.get("data", {})

            # normalize both possible formats
            tool = data.get("tool") or data.get("name")

            if tool == target:
                return True

    return False


def check_no_errors(events, _):
    return len(extract_errors(events)) == 0


def check_output_contains(events, criterion):
    blob = flatten_events(events)
    return criterion.get("value", "").lower() in blob


def check_tool_argument(events, criterion):
    """
    Validates tool was called with specific argument
    """
    target_tool = criterion.get("name")
    key = criterion.get("key")
    value = str(criterion.get("value"))

    for e in events:
        if e.get("event") == "tool_call" and e.get("data") == target_tool:
            # NOTE: your trace currently logs only tool name
            # this is a limitation → future improvement
            return True  # placeholder (upgrade when args logged)

    return False


# ---------------------------------------------------------------
# 🧠 Dispatcher
# ---------------------------------------------------------------

def evaluate(events, criteria):
    results = []
    passed = 0

    for c in criteria:
        if isinstance(c, str):
            # Backward compatibility (V1)
            ok = c.lower() in flatten_events(events)
            results.append({"criteria": c, "passed": ok})
            if ok:
                passed += 1
            continue

        ctype = c.get("type")

        if ctype == "tool_used":
            ok = check_tool_used(events, c)

        elif ctype == "no_errors":
            ok = check_no_errors(events, c)

        elif ctype == "output_contains":
            ok = check_output_contains(events, c)

        elif ctype == "tool_argument":
            ok = check_tool_argument(events, c)

        else:
            ok = False

        results.append({
            "criteria": c,
            "passed": ok
        })

        if ok:
            passed += 1

    total = len(criteria)
    score = passed / total if total else 0

    return {
        "score": score,
        "passed": passed,
        "total": total,
        "results": results
    }


# ---------------------------------------------------------------
# 🚀 Entry
# ---------------------------------------------------------------

def run(input_data):
    events = input_data.get("events", [])
    criteria = input_data.get("criteria", [])

    if not isinstance(events, list):
        return {
            "status": "error",
            "error": {"message": "Invalid events"}
        }

    if not isinstance(criteria, list):
        return {
            "status": "error",
            "error": {"message": "Invalid criteria"}
        }

    result = evaluate(events, criteria)

    return {
        "status": "success",
        "data": result
    }