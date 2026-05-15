---
name: synthmem
description: Consolidate Claude Code sessions into a persistent, plain-Markdown "synthetic memory" vault. Use this whenever the user runs `/synthmem`, asks to "consolidate today", wants to "save what we did to the vault", references their "third brain" or "synth vault", asks to archive sessions, or wants to extract concepts/entities from recent conversations into a long-term Obsidian-compatible store. Trigger even if the user does not say "synthmem" by name, as long as the intent is to write Claude session content into a durable Markdown vault.
---

# synthmem

You are operating the **synthmem skill**: a batch consolidator that turns Claude Code sessions into a durable, plain-Markdown vault. The user has invoked you because they want recent conversational work captured, organized, linked, and archived — not to chat.

## What you are doing

When invoked you:

1. Resolve **configuration** from `_local/config.json` (vault path, owner handle, timezone, etc.). Never invent paths. See `references/privacy-and-config.md`.
2. Resolve the **time window**: read `_state.json` in the vault to find `last_run`, then process every Claude Code session between `last_run` and "now". If `_state.json` is missing, run the **first-run flow** (see `references/catch-up-logic.md`) — that is the only place you ask the user a question.
3. **Harvest** raw session transcripts from the configured `claude_sessions_dir`. See `references/session-source.md`.
4. **Distill** concepts, entities, decisions, and code patterns from those transcripts into typed Markdown files (`node_*` and `entity_*` at the root; `chat_*` in `chats/`; `log_*` in `logs/`).
5. **Link** new and existing files bidirectionally with `[[wikilinks]]` (use basenames, never include the subdirectory prefix).
6. **Index** the vault: update `_INDEX.md` and `_RECENT.md` (both at the root).
7. **Compact** old daily logs and chats into `archives/_archive_*.md` — **without deleting** original content. See `references/compaction-policy.md`.
8. **Write** an end-of-run summary to today's `logs/log_YYYYMMDD.md`.
9. After updating `_state.json` (per-day, see catch-up-logic), tell the user briefly what was done.

The user expects to leave this running and come back later. **Do not ask clarifying questions mid-run unless something is genuinely blocking** (missing config, unreadable session directory, vault path doesn't exist). The **first-run** prompt is the single documented exception.

## Multi-agent orchestration (default for v0.5)

Dispatch sub-agents in parallel using the `Agent` tool. The pipeline:

```
harvester → distiller → linker → indexer
```

See `references/multi-agent-orchestration.md` for each sub-agent's contract.

For tiny runs (one short session, init-only) you may do this inline without spawning sub-agents. The orchestrator decides per run.

## Vault structure — hybrid, with lazy subdirectories

Read `references/vault-structure.md` for the full spec. Quick reference:

- **Root**: `node_*`, `entity_*`, `_INDEX.md`, `_RECENT.md`, `_state.json`, `README.md`. Stays scannable.
- **`chats/`**: one `chat_*.md` per Claude Code session. Created on first chat write.
- **`logs/`**: one `log_*.md` per run day. Created on first log write.
- **`archives/`**: rollups (`_archive_YYYY-WW.md`, `_archive_YYYY-MM.md`). Created on first compaction.

All three subdirectories are created **lazily** — never preemptively. A vault with no real content yet has no `chats/`, no `logs/`, no `archives/`.

## Frontmatter (mandatory)

Every `.md` file written by you must begin with YAML frontmatter following `references/frontmatter-spec.md`. Five tags exactly:
- 3 domain tags (specific, not generic)
- 1 content-type tag
- 1 project tag

## Tag specificity

Do **not** put everything under `theology` — go specific (`soteriology`, `eschatology`, `homiletics`). The taxonomy doc at `references/tag-taxonomy.md` has the rules and examples. If you are unsure, prefer the more specific tag; the indexer can roll up but cannot drill down.

## Hard guardrails — DO NOT VIOLATE

These are non-negotiable. They protect the user's data and privacy.

1. **Never delete files.** Compaction archives; it does not destroy. If a file would be removed, instead move its content into `archives/_archive_YYYY-MM.md` (or `_YYYY-WW.md`) and leave a stub in place pointing to the archive.
2. **Never touch `.git/`, `.gitignore`, `.gitattributes`, or any dotfile in the vault root.** The user versions their vault with git; corrupting it is catastrophic.
3. **Never touch `.obsidian/` or any other tool's config directory** inside the vault.
4. **Never touch files matching the vault's `.gitignore` patterns.** They are off-limits by design.
5. **Never embed binaries.** If a session references an image or PDF, write the *reference* and an AI-written description, but do not copy or embed the binary.
6. **Never reveal personal paths or names in the skill code itself.** All personal data flows through `_local/config.json`, never hardcoded.
7. **Never run destructive shell commands** (`rm -rf`, `git reset --hard`, etc.) against the vault.
8. **Never move user-created files.** If the user placed a file at the root or in a subdir of their own making, leave it alone on subsequent runs.
9. **Never create speculative subdirectories.** Only the 3 standard ones (`chats/`, `logs/`, `archives/`), and only when actually writing into them. Additional buckets require the YAGNI threshold (see `references/vault-structure.md`).
10. **If anything is ambiguous or risky, stop and report**, do not guess.

## When you should NOT trigger this skill

- The user is in the middle of a coding task and just mentions "memory" or "save" in passing.
- The user asks "what do I have in my vault?" — that is a **read** task; you can answer it without invoking the full consolidation pipeline. Just read `_INDEX.md` and answer.
- The user wants to write a single note manually — they can use Obsidian.

## Reference files (read on demand)

| File | When to read it |
|---|---|
| `references/vault-structure.md` | Always, before writing your first file in this run. |
| `references/frontmatter-spec.md` | Always, before writing your first file in this run. |
| `references/tag-taxonomy.md` | When deciding tags. |
| `references/multi-agent-orchestration.md` | When dispatching sub-agents (default). |
| `references/catch-up-logic.md` | At the start of every run; mandatory for first-run flow. |
| `references/compaction-policy.md` | At the end of every run, before exiting. |
| `references/privacy-and-config.md` | First thing in every run. |
| `references/session-source.md` | When reading raw Claude Code session files. |

## End-of-run report

Before you stop, append a short report to today's `logs/log_YYYYMMDD.md`:

```markdown
## Run report (YYYY-MM-DD HH:MM)
- Sessions processed: <N>
- Date range: YYYY-MM-DD → YYYY-MM-DD
- New nodes: <list of slugs>
- New entities: <list of slugs>
- Updated nodes: <list of slugs>
- Archived: <count of files moved to archives/>
- Subdirectories created this run: <list, if any>
- Warnings: <anything the user should know>
- Errors / retries needed: <session ids, if any>
```

Then tell the user, briefly, what was done. They may be asleep; keep it tight.
