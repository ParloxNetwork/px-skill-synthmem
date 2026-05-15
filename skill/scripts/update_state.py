#!/usr/bin/env python3
"""
update_state.py — atomic mutations to a vault's `_state.json`.

The vault state file tracks `last_run`, processed days, and pending sessions.
Mutations need to be atomic (interrupt-safe) and exclusive (no two writers).
This script handles both via a temp-file rename + advisory file lock.

Actions:
    init             — create `_state.json` with defaults (fails if it exists)
    mark-processed   — append a day to `processed_days`     (--value YYYY-MM-DD)
    add-pending      — append a session id to `pending_sessions` (--value ID)
    remove-pending   — remove a session id from `pending_sessions` (--value ID)
    finalize-run     — set last_run = now, status = completed
    set              — generic set: --value 'key=jsonValue'

Stdout: JSON of the updated state.
Exit codes:
    0 — OK
    1 — argument error
    2 — I/O error
    3 — invalid state file (parse error)
    4 — invalid action / value (e.g. init on existing file)
"""

import argparse
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VAULT_VERSION = "0.6.0"

DEFAULT_STATE = {
    "vault_version": VAULT_VERSION,
    "vault_created": None,
    "last_run": None,
    "last_run_status": "never",
    "last_run_range": None,
    "processed_days": [],
    "pending_sessions": [],
    "sessions_processed_total": 0,
    "current_streak_runs": 0,
    "schema": {"frontmatter": "1.0", "vault_layout": "1.0"},
}


def now_iso() -> str:
    """Local-tz ISO 8601 with offset, second precision."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_state(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(3)
    except OSError as e:
        print(f"I/O error reading {path}: {e}", file=sys.stderr)
        sys.exit(2)


def write_state_atomic(path: Path, state: dict):
    """Write to a temp file in the same dir, fsync, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--state-file", required=True,
                    help="Path to the vault's _state.json")
    ap.add_argument("--action", required=True,
                    choices=["init", "mark-processed", "add-pending",
                             "remove-pending", "finalize-run", "set"])
    ap.add_argument("--value", default=None)
    ap.add_argument("--range-from", default=None,
                    help="finalize-run: the 'from' side of last_run_range")
    args = ap.parse_args()

    path = Path(args.state_file).expanduser()

    # init is special — refuses if the file already exists
    if args.action == "init":
        if path.exists():
            print(f"State file already exists: {path}", file=sys.stderr)
            sys.exit(4)
        state = dict(DEFAULT_STATE)
        state["vault_created"] = now_iso()
        write_state_atomic(path, state)
        json.dump(state, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    state = read_state(path)
    if state is None:
        print(f"State file not found: {path}", file=sys.stderr)
        sys.exit(3)

    if args.action == "mark-processed":
        if not args.value:
            print("--value YYYY-MM-DD required for mark-processed", file=sys.stderr)
            sys.exit(1)
        days = state.setdefault("processed_days", [])
        if args.value not in days:
            days.append(args.value)

    elif args.action == "add-pending":
        if not args.value:
            print("--value SESSION_ID required for add-pending", file=sys.stderr)
            sys.exit(1)
        pending = state.setdefault("pending_sessions", [])
        if args.value not in pending:
            pending.append(args.value)

    elif args.action == "remove-pending":
        if not args.value:
            print("--value SESSION_ID required for remove-pending", file=sys.stderr)
            sys.exit(1)
        state["pending_sessions"] = [
            s for s in state.get("pending_sessions", []) if s != args.value
        ]

    elif args.action == "finalize-run":
        now = now_iso()
        state["last_run"] = now
        state["last_run_status"] = "completed"
        if args.range_from:
            state["last_run_range"] = {"from": args.range_from, "to": now}
        state["current_streak_runs"] = state.get("current_streak_runs", 0) + 1

    elif args.action == "set":
        if not args.value or "=" not in args.value:
            print("--value 'key=jsonValue' required for set", file=sys.stderr)
            sys.exit(1)
        key, _, raw = args.value.partition("=")
        try:
            state[key] = json.loads(raw)
        except json.JSONDecodeError:
            state[key] = raw

    write_state_atomic(path, state)
    json.dump(state, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
