# Catch-up logic

The user does not run `/synthmem` every day. The skill must figure out, on each invocation, what range of work to process — and recover gracefully if a previous run was interrupted.

## State file

The vault contains `_state.json` at its root. Structure:

```json
{
  "vault_version": "0.5.0",
  "last_run": "2026-05-12T23:47:00-05:00",
  "last_run_status": "completed",
  "last_run_range": {
    "from": "2026-05-10T00:00:00-05:00",
    "to": "2026-05-12T23:59:59-05:00"
  },
  "processed_days": ["2026-05-10", "2026-05-11", "2026-05-12"],
  "pending_sessions": [],
  "sessions_processed_total": 87,
  "current_streak_runs": 3
}
```

The `processed_days` array tracks which calendar days are fully consolidated. The `pending_sessions` array lists session IDs that started but failed (resilience — see below).

## Algorithm

### Step 1 — Read state

Open `_state.json`. Three cases:

| State | Treat as |
|---|---|
| File missing | First run — go to **first-run flow** below |
| File exists, `last_run_status: "completed"` | Normal incremental run |
| File exists, `last_run_status: "partial"` or `pending_sessions` non-empty | Resume — retry the pending work first, then continue |

### Step 1a — First-run flow

This is the single place the skill asks the user a question. Triggered when `_state.json` is missing.

Detect what's in the vault:

- **Empty vault** (no `node_*`, `entity_*`, `chats/`, `logs/`, only optional `.obsidian/` or similar tool config): pure first run.
- **Vault has prior content but no state**: the user imported a vault or deleted state. Treat the same way — ask.

Ask exactly once, in this format:

```
🆕 First run detected — vault has no _state.json yet.

   Vault path: ${VAULT_PATH}
   Claude Code session history found: <X> sessions across <Y> days
   Oldest session: <date>   |   Newest session: <date>

How should I bootstrap?
  [1] Today only         (fast — minutes)
  [2] Full history       (could take a long time — possibly hours
                          if you have months of sessions)
  [3] Custom window      (e.g., "last 30 days")
  [4] Cancel — don't write anything yet

Choice [1-4]:
```

Then act on the answer:

- `1`: process today only.
- `2`: process from oldest session to now. Use multi-agent dispatch (see `multi-agent-orchestration.md`). Warn one more time about duration before starting.
- `3`: parse the user's window (relative `30d`, `2w`, `1m` or absolute `YYYY-MM-DD`). Process that range.
- `4`: write a minimal `_state.json` (`last_run_status: "never"`) so the next invocation can still resume, but do nothing else. Exit.

After init, never ask again. Subsequent runs follow Step 2.

### Step 2 — Compute the time window

```
from = last_run         (the moment the previous run completed)
to   = now()
```

The range is `(last_run, now]` — exclusive of `last_run`, inclusive of `now`.

If `last_run_status == "partial"`: keep `last_run` unchanged so the new run reprocesses the same window. Pending sessions get priority (see Step 3a).

### Step 3 — Enumerate sessions in range

For each session file under `${CLAUDE_PROJECTS_DIR}/<project>/`:

- Parse its first event's `timestamp` (start of session).
- Parse its last event's `timestamp` (end of session).
- Include the session if it **overlaps** the range. (A session that started before `last_run` but continued past it should still be re-examined for the new portion.)

If a session was already partially processed in a previous run, the harvester re-distills only the new portion. Frontmatter `sources` on existing `node_*` files lets the linker dedupe.

### Step 3a — Resume pending sessions first

If `pending_sessions` is non-empty: process those first, in arrival order, before tackling the new window. A pending session that succeeds is removed from the array; one that fails again increments its retry counter (drop it after 3 attempts and warn the user in the run report).

### Step 4 — Group by day, process day-by-day

Group sessions by the day they occurred in (in vault timezone). For each day, in chronological order:

1. The harvester writes that day's `chats/chat_*.md` files.
2. The distiller writes `node_*` / `entity_*` updates derived from that day.
3. The linker reconciles wikilinks for files touched that day.
4. The indexer writes that day's `logs/log_YYYYMMDD.md`.
5. **`_state.json` is updated with that day appended to `processed_days`.**

This per-day commit cadence is the key resilience feature: a process kill, power loss, or connection drop during day N+1 leaves days 1..N fully consolidated and recorded. The next run picks up from day N+1.

### Step 5 — Final state update

When all days in the window succeed, finalize `_state.json`:

```json
{
  "last_run": "<now>",
  "last_run_status": "completed",
  "last_run_range": {"from": "<previous last_run>", "to": "<now>"},
  "processed_days": [...],
  "pending_sessions": [...still-failing ones, if any...],
  "sessions_processed_total": <old + this_run>,
  "current_streak_runs": <old + 1>
}
```

If any day failed past 3 retries, leave `last_run_status: "partial"` so the user notices. The run report includes a `## Errors` section listing the failures.

## Edge cases

### Ran an hour ago, runs again

`from = an hour ago`, `to = now`. Probably zero or one session. Process and exit quickly.

### Silent for a month

`from = a month ago`. Could be 0 sessions or hundreds. Dispatch sub-agents; process day-by-day so an interrupt doesn't waste work.

### Clock skew / DST transitions

Always use ISO 8601 with timezone offset. Never store naive timestamps. DST transitions still sort correctly.

### Multiple machines (sync)

The skill does not solve sync; that's the user's job (Dropbox, git, etc.). Absolute timestamps make the catch-up window correct across machines. The only risk is **concurrent** runs from two machines simultaneously; v0.5 does not prevent that. Addressed in v1.0.

### First-ever run on a vault that already has content

If `_state.json` is missing but the vault has `node_*` files (imported vault, deleted state, etc.): go through the first-run flow and ask. The vault's existing content is not touched — only new processing is added.
