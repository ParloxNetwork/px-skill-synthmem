# skill/scripts/

Optional Python helpers that accelerate `/synthmem` runs.

> **The skill works without these.** If Python 3 is missing or a script fails, the skill falls back to inline AI parsing (using the rules in `references/session-source.md`). Having Python 3.8+ unlocks the fast, deterministic path.

## Contract

- **Python 3.8+ stdlib only.** No `pip install` required. No third-party imports.
- **No network I/O.** Ever. (The skill would fail loud if a script tried.)
- **Read-only on the Claude Code sessions directory.** Never modifies session transcripts.
- **Writes only to the vault's `_state.json`** (via `update_state.py`).
- **Atomic file writes** (temp file + `os.replace`) with `fcntl.flock` for advisory locking.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | OK |
| `1` | Argument error |
| `2` | I/O error |
| `3` | File not found or unparseable |
| `4` | Invalid action / value |
| `5` | Validation found ERROR-level issues (`validate_vault.py` only) |

The skill interprets exit codes without parsing stdout (stdout is reserved for the JSON payload, stderr for human-readable errors).

## Scripts

### `find_sessions.py`

List Claude Code session JSONL files that overlap a date range.

```bash
python3 find_sessions.py \
  --projects-dir ~/.claude/projects \
  --from 2026-05-01T00:00:00-05:00 \
  --to   2026-05-14T23:59:59-05:00
```

**Stdout**: JSON array `[{session_id, jsonl_path, project_dir, started_at, ended_at}, ...]`

### `validate_vault.py`

Deterministic, read-only health check. Never modifies the vault — reports only.

```bash
# JSON (for the skill to parse)
python3 validate_vault.py --vault /path/to/vault

# Human-readable
python3 validate_vault.py --vault /path/to/vault --format text
```

Checks: frontmatter completeness, `type`↔subdir, slug==filename-tail, 5 distinct tags, content-type vocabulary, ISO dates, broken/asymmetric/isolated wikilinks, dangling targets that should be stubs (≥3 refs), near-duplicate slugs/titles, raw `<...>`/pipe/leading-`#` markdown hazards, binaries, root cleanliness.

**Stdout**: JSON `{summary:{errors,warnings,info,verdict}, errors[], warnings[], info[]}`. **Exit 5** if any ERROR-level issue (so a CI step or the skill can gate on it); exit 0 if only warnings/info.

Two ways it runs:
- **End of every `/synthmem`** — the indexer invokes it; findings go into the daily log report and `_state.json` is finalized only if there are no ERRORs.
- **Standalone** `/synthmem validate` — read-only, no consolidation. Cheap way to audit a large existing vault without reprocessing.

### `parse_session.py`

Parse one JSONL file into a structured object.

```bash
python3 parse_session.py \
  --jsonl-path ~/.claude/projects/foo/abc-123.jsonl \
  --redact-cwd
```

**Stdout**: JSON object with `session_id`, `started_at`, `ended_at`, `cwd`, `summary_hint`, `turn_count`, `turns: [...]`. Each turn groups a user message, the assistant's response, and intervening tool events.

`--redact-cwd` replaces `working_directory` with `<redacted>`. Use when the skill is configured with `record_cwd_in_chats: false`.

### `update_state.py`

Atomic mutation of a vault's `_state.json`.

```bash
# Initialize a new state file (fails if it exists)
python3 update_state.py --state-file VAULT/_state.json --action init

# Mark a day as fully processed
python3 update_state.py --state-file VAULT/_state.json --action mark-processed --value 2026-05-14

# Add / remove a pending session
python3 update_state.py --state-file VAULT/_state.json --action add-pending --value <session-id>
python3 update_state.py --state-file VAULT/_state.json --action remove-pending --value <session-id>

# Finalize the run (sets last_run = now, status = completed)
python3 update_state.py --state-file VAULT/_state.json --action finalize-run --range-from 2026-05-13T00:00:00-05:00

# Generic set: any key, any JSON-valued value
python3 update_state.py --state-file VAULT/_state.json --action set --value 'sessions_processed_total=42'
```

## Why scripts (instead of inline AI parsing)

| Task | Inline AI | Script |
|---|---|---|
| Parse a 100-turn JSONL | ~5,000 tokens, possible hallucination | <100 ms, deterministic |
| Update `_state.json` | Error-prone JSON merge | Atomic, file-locked |
| List sessions in a date range | Per-file decision logic | Single fast pass |

The skill detects script availability at the start of every run. If `python3` is on PATH and the scripts are present, it uses them. Otherwise it falls back to the inline rules in `references/session-source.md` and notes the degradation in the run report.
