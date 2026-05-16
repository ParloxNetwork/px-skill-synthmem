#!/usr/bin/env python3
"""
status_vault.py — read-only operational dashboard for a synthmem vault.

Distinct from validate_vault.py (correctness gate) and repair_vault.py
(fixer): this is the "how's my vault doing" summary. Reads `_state.json`
and the filesystem; never modifies anything, never re-runs validation
(that's `/synthmem validate`). Fast even on large vaults.

Reports: vault path + size, last-run timestamp/status, totals & streak,
pending sessions, per-subdir file counts, draft-stub count, and how many
calendar days have elapsed since the last run (a cheap "you have work
waiting" hint without scanning sessions).

Stdout: human-readable by default, or JSON with --format json.
Exit codes:
    0 — OK
    1 — argument error
    2 — I/O error
    3 — vault path not found
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SUBDIRS = ["nodes", "entities", "chats", "logs", "archives"]


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def parse_iso(s):
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def count_draft_stubs(vault):
    n = 0
    for sub in ("nodes", "entities"):
        d = vault / sub
        if not d.is_dir():
            continue
        for p in d.glob("*.md"):
            head = p.read_text(encoding="utf-8", errors="replace")[:600]
            if re.search(r"^status:\s*draft\s*$", head, re.M):
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--vault", required=True)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    if not vault.is_dir():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(3)

    try:
        state = {}
        sp = vault / "_state.json"
        if sp.is_file():
            try:
                state = json.loads(sp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                state = {"_parse_error": True}

        counts, total_files, total_bytes = {}, 0, 0
        for sub in SUBDIRS:
            d = vault / sub
            c = 0
            if d.is_dir():
                for p in d.glob("*.md"):
                    c += 1
                    total_bytes += p.stat().st_size
            counts[sub] = c
            total_files += c
        for meta in ("_INDEX.md", "_RECENT.md", "_state.json", "README.md"):
            mp = vault / meta
            if mp.is_file():
                total_bytes += mp.stat().st_size

        drafts = count_draft_stubs(vault)
        pending = state.get("pending_sessions", []) or []
        last_run = state.get("last_run")
        lr = parse_iso(last_run)
        days_since = None
        if lr:
            days_since = (datetime.now(timezone.utc).astimezone()
                          - lr).days
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        sys.exit(2)

    data = {
        "vault_path": str(vault),
        "vault_size": human_size(total_bytes),
        "last_run": last_run,
        "last_run_status": state.get("last_run_status", "unknown"),
        "days_since_last_run": days_since,
        "sessions_processed_total": state.get("sessions_processed_total"),
        "current_streak_runs": state.get("current_streak_runs"),
        "pending_sessions": pending,
        "counts": counts,
        "total_content_files": total_files,
        "draft_stubs": drafts,
        "schema": state.get("schema"),
    }

    if args.format == "json":
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.exit(0)

    print(f"synthmem vault status — {vault}")
    print(f"  size:            {data['vault_size']} "
          f"({total_files} content files)")
    print(f"  last run:        {last_run or 'never'} "
          f"[{data['last_run_status']}]"
          + (f"  ({days_since} day(s) ago)" if days_since is not None
             else ""))
    print(f"  total processed: {data['sessions_processed_total']} sessions"
          f"   streak: {data['current_streak_runs']}")
    print(f"  files:           "
          + "  ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"  draft stubs:     {drafts}"
          + ("  (concepts awaiting a session to flesh them out)"
             if drafts else ""))
    if pending:
        print(f"  ⚠ pending:       {len(pending)} session(s) need retry "
              f"— run `/synthmem --retry`")
        for s in pending[:10]:
            print(f"      - {s}")
    else:
        print("  pending:         none")
    if days_since is not None and days_since >= 1:
        print(f"\n  → {days_since} day(s) since last run. Run `/synthmem` "
              f"to consolidate the gap.")
    print("\n  (read-only snapshot; run `/synthmem validate` for a "
          "correctness check)")
    sys.exit(0)


if __name__ == "__main__":
    main()
