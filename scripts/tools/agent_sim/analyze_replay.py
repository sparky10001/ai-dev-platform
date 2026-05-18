#!/usr/bin/env python3
###################################################################
# analyze_replay.py — Analyze agent-sim replay files (MCP-compliant v1.0)
#
# Purpose:
#   Loads and analyzes replay logs from agent-sim (JSONL format)
#   Provides statistics, success rate, path analysis, and summaries.
###################################################################

import json
from pathlib import Path
from typing import Any, Dict, List

name = "analyze_replay"
description = "Analyze an agent-sim replay file (.jsonl) and return detailed performance statistics"

# ================================================================
# 🧾 INPUT SCHEMA
# ================================================================

input_schema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to the replay file (.jsonl)"
        },
        "max_events": {
            "type": "integer",
            "description": "Maximum number of events to load (for large files)",
            "default": 10000
        }
    },
    "required": ["path"]
}

# ================================================================
# 🧱 RESPONSE HELPERS
# ================================================================

def success(data: Dict, meta=None):
    return {
        "status": "success",
        "data": data,
        "error": None,
        "meta": meta or {}
    }

def failure(message: str, error_type="tool_error", meta=None):
    return {
        "status": "error",
        "data": None,
        "error": {
            "message": message,
            "type": error_type
        },
        "meta": meta or {}
    }

# ================================================================
# 🚀 MAIN
# ================================================================

def run(input_data: Dict[str, Any]):
    try:
        rel_path = input_data.get("path")
        max_events = int(input_data.get("max_events", 10000))

        if not isinstance(rel_path, str) or not rel_path.strip():
            return failure("Missing or invalid 'path'", "validation_error")

        replay_path = Path(rel_path)
        if not replay_path.is_absolute():
            # Try relative to workspace or common log locations
            workspace = os.getenv("AI_WORKSPACE_DIR") or os.getcwd()
            replay_path = Path(workspace) / replay_path

        if not replay_path.exists():
            return failure(f"Replay file not found: {replay_path}", "not_found")

        if not replay_path.is_file():
            return failure(f"Path is not a file: {replay_path}", "validation_error")

        events: List[Dict] = []
        episode_stats = []

        current_episode = []
        episode_count = 0

        with open(replay_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_events:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    events.append(event)

                    # Basic episode tracking
                    if event.get("event") == "session_start" or event.get("type") == "meta":
                        if current_episode:
                            episode_count += 1
                            episode_stats.append(len(current_episode))
                        current_episode = []
                    current_episode.append(event)

                except json.JSONDecodeError:
                    continue

        # Final episode
        if current_episode:
            episode_count += 1
            episode_stats.append(len(current_episode))

        # Basic metrics
        total_steps = len([e for e in events if e.get("event") in ("tool_call", "step")])
        success_events = len([e for e in events if e.get("data", {}).get("done") is True or 
                                           e.get("event") == "session_end" and 
                                           e.get("data", {}).get("status") == "success"])

        avg_episode_length = sum(episode_stats) / len(episode_stats) if episode_stats else 0

        result = {
            "replay_path": str(replay_path),
            "total_events": len(events),
            "episode_count": episode_count,
            "total_steps": total_steps,
            "success_events": success_events,
            "avg_episode_length": round(avg_episode_length, 2),
            "success_rate_estimate": round(success_events / max(episode_count, 1), 4),
            "file_size_bytes": replay_path.stat().st_size,
            "max_events_processed": max_events
        }

        return success(result, meta={"tool": "analyze_replay"})

    except Exception as e:
        return failure(f"Failed to analyze replay: {str(e)}", "execution_error")


# For quick local testing
if __name__ == "__main__":
    test_input = {"path": "example_replay.jsonl"}
    result = run(test_input)
    print(result)