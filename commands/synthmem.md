---
name: synthmem
description: Consolidate recent Claude Code sessions into your synthetic-memory vault.
argument-hint: "[init | status | --since DATE | --dry-run]"
---

# /synthmem

Run the synthmem consolidation flow. Invokes the `synthmem` skill (installed at `~/.claude/skills/synthmem/`) and processes Claude Code sessions into your plain-Markdown vault.

## Usage

| Form | Effect |
|---|---|
| `/synthmem` | Default: run catch-up from `_state.json.last_run` to now. If first run, prompts once for the look-back window. |
| `/synthmem init` | Bootstrap a new vault at `vault_path` (creates `_INDEX.md`, `_RECENT.md`, `_state.json`, `README.md`). Idempotent — won't clobber an existing vault. |
| `/synthmem status` | Read-only. Reports last run, pending sessions, vault size, warnings. |
| `/synthmem validate` | Read-only. Runs the deterministic vault validator (frontmatter, slugs, tags, wikilinks, duplicates, markdown safety) and prints PASS/REVIEW/FAIL. No consolidation, no writes. Cheap way to audit a large vault. |
| `/synthmem repair` | Manual reconcile of an existing vault (tag distinctness, slug==filename-tail, missing reverse wikilinks, archive content-type, render-breaking `<…>`). Never deletes content. **Note: as of v0.6.6 this runs automatically inside every `/synthmem` run when the validator finds fixable drift** — you only need this subcommand for a manual/standalone pass or debugging. Routine operation is hands-off. |
| `/synthmem --since YYYY-MM-DD` | Override the start of the catch-up window. |
| `/synthmem --since 7d` | Same, but relative (`7d`, `2w`, `1m`). |
| `/synthmem --dry-run` | Preview only. Resolves config, computes the window, harvests sessions, and plans the distillation/linking/compaction at the metadata level — then prints a structured plan and exits having written **nothing** (no files, no subdirs, no `_state.json`). Combine with `--since`. The safe "what would happen if I run this?" check. |

## What it does

1. Loads `_local/config.json` (from the skill repo) for vault path, owner handle, timezone.
2. Reads `_state.json` to determine the date range to process.
3. Reads Claude Code session transcripts from `claude_sessions_dir`.
4. Dispatches sub-agents (harvester → distiller → linker → indexer) to consolidate.
5. Writes/updates `node_*.md`, `entity_*.md` at the vault root; `chats/chat_*.md` and `logs/log_*.md` in their subdirectories (created lazily).
6. Updates `_INDEX.md`, `_RECENT.md`, `_state.json` (state is checkpointed day-by-day for resilience).
7. Runs compaction (archive into `archives/`, never delete) if cadence is due.
8. Reports a concise summary.

## Guarantees

- **Idempotent.** Running twice with the same date range produces no duplicate work — `_state.json` tracks what's already processed.
- **Non-destructive.** Nothing in the vault is ever deleted. Old daily logs and chats are archived into `archives/_archive_*.md` files; originals stay.
- **Privacy-respecting.** Reads `_local/` config; never hardcodes personal paths or names. No personal data leaves your machine.
- **Resumable.** If interrupted, the next run picks up where the previous one left off.
- **Hands-off.** Designed to run unattended (e.g., end-of-day cron-like usage). Will not interrupt to ask questions unless something is genuinely blocking.

## Invocation

When you run `/synthmem`, Claude will:

1. Read `~/.claude/skills/synthmem/SKILL.md` for the operating instructions.
2. Resolve config and state.
3. Execute the consolidation pipeline.
4. Report results back to you in this chat.

You can leave the conversation running and return later — synthmem will work through any backlog and stop when done.

## Errors

- **"Config not found"**: copy `config.example.json` (at the skill repo root) → `_local/config.json` and set `vault_path`.
- **"Vault path doesn't exist"**: either point `vault_path` at an existing folder or run `/synthmem init`.
- **"No sessions in range"**: nothing happened in the date window. No-op. `_state.json` is still bumped.
- **"Sub-agent failed"**: partial progress is preserved; the next run resumes.

See `~/.claude/skills/synthmem/SKILL.md` for the full operational contract.
