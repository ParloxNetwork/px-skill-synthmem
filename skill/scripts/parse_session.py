#!/usr/bin/env python3
"""
parse_session.py — parse a Claude Code JSONL session into structured turns.

Output: a single JSON object with session metadata + an array of turns. Each
turn groups a user message, the assistant's response, and any tool_use /
tool_result events that occurred between them.

Stdout: JSON object
Exit codes:
    0 — OK
    1 — argument error
    2 — I/O error
    3 — file not found / unparseable
"""

import argparse
import json
import sys
from pathlib import Path

# Event types we consider when building turns. Anything else is dropped.
INTERESTING_TYPES = {
    "user", "assistant", "tool_use", "tool_result", "summary", "system",
}


def _extract_content(event: dict) -> str:
    """Best-effort text extraction from a Claude Code event."""
    msg = event.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        parts.append(part["text"])
                    elif "content" in part:
                        parts.append(str(part["content"]))
            return "\n".join(parts)
        if isinstance(content, str):
            return content
    return event.get("content", "") or ""


def _group_into_turns(events):
    """A turn = user message + assistant response + intervening tool events."""
    turns = []
    current = None
    for e in events:
        etype = e["type"]
        if etype == "user":
            if current:
                turns.append(current)
            current = {"user": e, "assistant": None, "tools": []}
        elif etype == "assistant":
            if current is None:
                current = {"user": None, "assistant": e, "tools": []}
            else:
                current["assistant"] = e
        elif etype in ("tool_use", "tool_result"):
            if current is None:
                current = {"user": None, "assistant": None, "tools": [e]}
            else:
                current["tools"].append(e)
        else:
            if current is not None:
                current.setdefault("extras", []).append(e)
    if current is not None:
        turns.append(current)
    return turns


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--jsonl-path", required=True)
    ap.add_argument("--redact-cwd", action="store_true",
                    help="Replace working_directory with <redacted> in output")
    args = ap.parse_args()

    path = Path(args.jsonl_path).expanduser()
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(3)

    events = []
    summary_hint = None
    started_at = None
    ended_at = None
    cwd = None

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = obj.get("type", "unknown")
                ts = obj.get("timestamp")

                if etype == "summary":
                    if "summary" in obj:
                        summary_hint = obj["summary"]
                if cwd is None and "cwd" in obj:
                    cwd = obj["cwd"]

                if etype not in INTERESTING_TYPES:
                    continue

                if ts:
                    if started_at is None:
                        started_at = ts
                    ended_at = ts

                events.append({
                    "type": etype,
                    "timestamp": ts,
                    "content": _extract_content(obj),
                })
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        sys.exit(2)

    turns = _group_into_turns(events)

    if args.redact_cwd:
        cwd = "<redacted>"

    out = {
        "session_id": path.stem,
        "started_at": started_at,
        "ended_at": ended_at,
        "cwd": cwd,
        "summary_hint": summary_hint,
        "turn_count": len(turns),
        "turns": turns,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
