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

Checks: frontmatter completeness, `type`↔subdir, slug==filename-tail, 5 distinct tags, content-type vocabulary, ISO dates, broken/asymmetric/isolated wikilinks, dangling targets that should be stubs (≥3 refs), near-duplicate slugs/titles, raw `<...>`/pipe/leading-`#` markdown hazards, binaries, root cleanliness, **tag-genericity** (advisory warning: umbrella term from the curated denylist in a domain slot — never an error, never auto-fixed; v0.6.10).

**Stdout**: JSON `{summary:{errors,warnings,info,verdict}, errors[], warnings[], info[]}`. **Exit 5** if any ERROR-level issue (so a CI step or the skill can gate on it); exit 0 if only warnings/info.

`--changed "a.md,b.md,…"` (scope-aware gate): ERRORs in listed files stay ERRORs; ERRORs in files NOT listed are demoted to warnings tagged "pre-existing (run /synthmem repair)". The run gate passes the files it touched so legacy issues don't block finalization forever.

Two ways it runs:
- **End of every `/synthmem`** — the indexer invokes it with `--changed`; findings go into the daily log; `_state.json` finalized only if zero *in-scope* ERRORs.
- **Standalone** `/synthmem validate` — read-only, no `--changed`, whole-vault audit.

### `repair_vault.py`

Deterministic reconcile/fix pass. The validator *detects*; this *fixes*. Modifies files in place but **never deletes content** — only rewrites specific frontmatter fields, adds missing reverse wikilinks, backticks render-breaking tokens; bumps `last_updated`.

```bash
python3 repair_vault.py --vault /path/to/vault --project synthmem-dev
python3 repair_vault.py --vault /path/to/vault --format text       # human-readable
python3 repair_vault.py --vault /path/to/vault --links-only         # graph-integrity only
```

Full fixes: meta/archive/log tag normalization to the canonical 5-distinct tuple; `slug` → filename-stem-minus-prefix; missing reverse wikilinks; ≥3-ref `node_`/`entity_` stub materialization; archive content-type → `summary`; bare `<…>` → backticked. Genuine duplicate-domain-tags on `node_`/`entity_` are **flagged, not auto-fixed** (need semantic re-tag).

`--links-only` (v0.6.7): runs **only** the deterministic graph-integrity pass — reverse-link symmetrization + ≥3-ref stub materialization (both `node_` and `entity_`). Skips tag/slug/markdown repairs. The **linker sub-agent calls this as its mandatory phase-3 final step** so the validation gate never sees asymmetric links and there is no per-run auto-heal churn (v0.6.6 observability proved the LLM linker emits ~176 asymmetric links/run that repair was cleaning every time). On the post-v0.6.6 test vault: REVIEW (16 warnings) → **PASS (0 warnings)**, 16 node-stubs created.

**Stdout**: JSON `{summary, fixed[], flagged[]}`. Exit 0 always (it is a fix tool, not a gate). On the v0.6.2 test vault it took the verdict from FAIL (6 errors / 130 warnings) to REVIEW (0 errors / 2 warnings). Invoked by `/synthmem repair`; recommended by the gate whenever pre-existing errors appear.

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

# Bump a failed session's retry counter (auto-drops after 3 attempts into
# dropped_sessions so a broken session never loops forever)
python3 update_state.py --state-file VAULT/_state.json --action bump-retry --value <session-id>

# Finalize the run (sets last_run = now, status = completed)
python3 update_state.py --state-file VAULT/_state.json --action finalize-run --range-from 2026-05-13T00:00:00-05:00

# Generic set: any key, any JSON-valued value
python3 update_state.py --state-file VAULT/_state.json --action set --value 'sessions_processed_total=42'
```

### `status_vault.py`

Read-only operational dashboard (distinct from `validate_vault.py` correctness, `repair_vault.py` fixes). Reads `_state.json` + filesystem; never writes, never re-validates. Fast on large vaults.

```bash
python3 status_vault.py --vault /path/to/vault            # human-readable
python3 status_vault.py --vault /path/to/vault --format json
```

Reports: vault size + per-subdir file counts, last-run timestamp/status, total sessions processed + streak, draft-stub count, pending sessions (+ retry hint), days since last run. Backs `/synthmem status`.

## Why scripts (instead of inline AI parsing)

| Task | Inline AI | Script |
|---|---|---|
| Parse a 100-turn JSONL | ~5,000 tokens, possible hallucination | <100 ms, deterministic |
| Update `_state.json` | Error-prone JSON merge | Atomic, file-locked |
| List sessions in a date range | Per-file decision logic | Single fast pass |
| Validate the whole vault | Inconsistent eyeballing | Reproducible, exit-coded |
| Repair legacy issues | Risky freehand edits | Field-targeted, content-safe |

The skill detects script availability at the start of every run. If `python3` is on PATH and the scripts are present, it uses them. Otherwise it falls back to the inline rules in `references/session-source.md` and notes the degradation in the run report.
