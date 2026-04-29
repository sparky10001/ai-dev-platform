import json

name = "compare_results"
description = "Compare two evaluation result files"

def load(path):
    with open(path, "r") as f:
        return json.load(f)

def run(input_data):
    baseline_path = input_data.get("baseline")
    current_path = input_data.get("current")

    if not baseline_path or not current_path:
        return {"status": "error", "error": {"message": "Missing paths"}}

    try:
        base = load(baseline_path)
        curr = load(current_path)
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

    score_diff = curr["score"] - base["score"]

    regressions = []
    improvements = []

    base_results = base.get("results", [])
    curr_results = curr.get("results", [])

    for i, b in enumerate(base_results):
        c = curr_results[i] if i < len(curr_results) else None
        if not c:
            continue

        if b["passed"] and not c["passed"]:
            regressions.append(b["criteria"])

        if not b["passed"] and c["passed"]:
            improvements.append(b["criteria"])

    return {
        "status": "success",
        "data": {
            "baseline_score": base["score"],
            "current_score": curr["score"],
            "score_diff": score_diff,
            "regressions": regressions,
            "improvements": improvements,
            "regressed": score_diff < 0
        }
    }