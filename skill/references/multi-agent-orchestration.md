# Multi-agent orchestration

Synthmem runs as a pipeline of specialized sub-agents. Each does one thing well; the orchestrator (you, the main skill invocation) coordinates them.

## Why multi-agent

A single long-running Claude session would carry the entire vault, all session transcripts, and all reasoning in one context. That's expensive, slow, and fragile. Splitting the work:

- Each sub-agent has a tight, focused prompt.
- Failures are isolated (a broken distiller doesn't corrupt the indexer's work).
- The main session orchestrates and reports — it doesn't need to hold every transcript in its context.

## The pipeline

```
                      ┌─────────────┐
   _state.json   ───→ │  orchestrator  ──→ end-of-run report
   _local/config      │   (this skill)  │
                      └────┬────────┘
                             │
                ┌───────────┼───────────┐
                ▼            ▼            ▼
          ┌─────────┐  ┌─────────┐  ┌─────────┐
          │harvester│→ │distiller│→ │ linker  │ → ┌─────────┐
          └─────────┘  └─────────┘  └─────────┘    │ indexer │
                                                    └─────────┘
```

## Sub-agent specs

### 1. `harvester`

**Job:** Read raw Claude Code session files in the date range and produce `chat_*.md` references (one per session).

**Inputs (passed in prompt):**
- Date range (`from`, `to`)
- `claude_sessions_dir` (from config)
- Vault path

**Outputs:**
- One `chats/chat_YYYYMMDD_<short-id>.md` per session (creates `chats/` lazily on first write), with:
  - Frontmatter (type: chat, tags including session topic guesses, content-type: `summary`)
  - A ~5–15 line distilled summary of what the session was about
  - Pointers to the raw `.jsonl` file (path only, not embedded)
  - Lists of candidate concepts and entities for the distiller to pick up
- A handoff JSON listing the `chat_*` files it produced + concept/entity candidates

**Must not:** create `node_*` or `entity_*` files (that's the distiller's job).

### 2. `distiller`

**Job:** Take the candidate list from the harvester and produce/update `node_*.md` and `entity_*.md` files.

**Inputs:**
- The harvester's handoff JSON
- Vault path (for checking what already exists)
- Tag taxonomy reference

**Outputs:**
- New `node_*.md` files for concepts not yet in the vault
- **Append blocks** to existing `node_*.md` files when the concept already exists (do not overwrite — append a dated section)
- Same for `entity_*.md`
- A handoff JSON listing files created and files updated, with the wikilinks each contains

**Must not:**
- Overwrite existing `node_*` or `entity_*` files entirely. Append, or refactor only if explicitly justified in the handoff JSON.
- Duplicate concepts under near-identical slugs (`node_justification` vs `node_justification-doctrine`). Search the vault first; reuse the existing slug.

### 3. `linker`

**Job:** Enforce bidirectional wikilinks.

**Inputs:**
- The distiller's handoff JSON
- Vault path

**Logic:**
- For each file touched by the distiller, parse its `linked_nodes` list.
- For each `[[target]]` in the list, open `target.md` and ensure `linked_nodes` contains a back-link to the source.
- Detect and remove broken wikilinks (target file doesn't exist) — log them as warnings rather than deleting silently.

**Outputs:**
- Updated files (only `linked_nodes` and `last_updated` fields change)
- A handoff JSON: links added, links removed, warnings.

### 4. `indexer`

**Job:** Update `_INDEX.md`, `_RECENT.md`, `_state.json`, run compaction.

**Inputs:**
- All previous handoffs
- Vault path
- Compaction policy reference

**Outputs:**
- `_INDEX.md` regenerated from a scan of all `node_*` and `entity_*` frontmatter.
- `_RECENT.md` updated with the last 14 days of activity (older entries dropped from this file but never from the vault).
- `_state.json` `last_run` bumped to "now".
- Compaction performed per `compaction-policy.md`.
- A final summary appended to today's `logs/log_YYYYMMDD.md` (creates `logs/` lazily on first write).
- `_state.json` updated **after each day completes**, not only at the very end — see `catch-up-logic.md` for the resilience model.

### 5. `reviewer` (optional, off by default)

**Job:** Sanity-check the run before exit. Look for:
- Frontmatter that doesn't parse
- Duplicate slugs
- Tags outside the taxonomy
- Wikilinks to non-existent files
- Files written outside the prefix system

**Outputs:** a `WARNINGS` section appended to today's log if anything is off. Does **not** auto-correct — flags only.

Enable via `_local/config.json` → `agents.reviewer: true`.

## Dispatch

When the work is non-trivial (> 1 day of sessions, or > 5 sessions in any day), dispatch sub-agents using the `Agent` tool. For trivial runs (first-time init, single short session), do the work inline.

Each sub-agent's prompt should include:
- A clear scope statement ("you are the X; do only X")
- The handoff inputs (passed as literal text or file paths)
- Pointers to the relevant reference files in this skill
- A schema for the handoff output JSON

Sub-agents must **not** call the main `/synthmem` recursively.

## Failure modes

If a sub-agent fails:
- The orchestrator keeps whatever the previous agents produced (no rollback).
- Today's log records the failure in `WARNINGS`.
- The user can rerun `/synthmem` and the catch-up logic will reprocess what was missed.

Never leave the vault in an inconsistent state: if you cannot complete the run, at minimum ensure `_state.json.last_run` is **not** updated (so the next run reprocesses the same range).
