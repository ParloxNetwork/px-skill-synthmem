#!/usr/bin/env python3
"""
find_sessions.py — list Claude Code sessions overlapping a date range.

Stream-reads the first and last `timestamp` field of every `*.jsonl` file under
the configured projects directory and emits a JSON array of sessions whose
timespan overlaps the requested range.

Stdout: JSON array `[{"session_id", "jsonl_path", "project_dir",
                      "started_at", "ended_at"}]`
Exit codes:
    0 — OK
    1 — argument error
    2 — I/O error
    3 — projects directory not found
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def parse_iso(s: str) -> datetime:
    """Parse ISO 8601. Accepts trailing 'Z'."""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def stream_first_last_timestamps(jsonl_path: Path):
    """Return (first_ts, last_ts) by streaming the JSONL once."""
    first = None
    last = None
    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = obj.get("timestamp")
                if ts:
                    if first is None:
                        first = ts
                    last = ts
    except OSError:
        return None, None
    return first, last


def overlaps(start_iso, end_iso, range_from, range_to):
    if not start_iso or not end_iso:
        return False
    try:
        s_start = parse_iso(start_iso)
        s_end = parse_iso(end_iso)
    except ValueError:
        return False
    return s_end >= range_from and s_start <= range_to


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--projects-dir", required=True,
                    help="Claude Code projects directory (usually ~/.claude/projects)")
    ap.add_argument("--from", dest="range_from", required=True,
                    help="ISO 8601 datetime, e.g. 2026-05-01T00:00:00-05:00")
    ap.add_argument("--to", dest="range_to", required=True,
                    help="ISO 8601 datetime, e.g. 2026-05-14T23:59:59-05:00")
    args = ap.parse_args()

    try:
        rfrom = parse_iso(args.range_from)
        rto = parse_iso(args.range_to)
    except ValueError as e:
        print(f"Invalid date: {e}", file=sys.stderr)
        sys.exit(1)

    projects_dir = Path(args.projects_dir).expanduser()
    if not projects_dir.is_dir():
        print(f"Projects directory not found: {projects_dir}", file=sys.stderr)
        sys.exit(3)

    results = []
    try:
        for project_dir in sorted(projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl in sorted(project_dir.glob("*.jsonl")):
                first, last = stream_first_last_timestamps(jsonl)
                if not first or not last:
                    continue
                if overlaps(first, last, rfrom, rto):
                    results.append({
                        "session_id": jsonl.stem,
                        "jsonl_path": str(jsonl),
                        "project_dir": project_dir.name,
                        "started_at": first,
                        "ended_at": last,
                    })
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        sys.exit(2)

    json.dump(results, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
