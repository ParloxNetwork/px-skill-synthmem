# <Vault name>

> A synthetic-memory vault, populated by the [synthmem](https://github.com/your-handle/px-skill-synthmem) Claude Code skill.

## What this is

A hybrid-Markdown "third brain" — a persistent memory of work done with AI assistants, structured for both AI and human readability. Semantic content lives at the root; high-cardinality transient files live in subdirectories.

The skill writes here. You read here. Run `/synthmem` (typically end-of-day) to consolidate recent sessions into this vault.

## How to read it

- Open in [Obsidian](https://obsidian.md) for graph view and wikilink navigation.
- Or browse with any text editor / `grep` / `rg` — every file is plain Markdown.
- Start with [[_INDEX]] (full inventory) or [[_RECENT]] (last 14 days).

## Layout

```
vault-root/
├── README.md              ← this file
├── _INDEX.md              ← inventory, auto-generated
├── _RECENT.md             ← last 14 days, auto-generated
├── _state.json            ← machine state (last-run, etc.)
├── node_*.md              ← concepts (atomic knowledge)
├── entity_*.md            ← people, tools, projects, AIs
├── chats/                 ← one file per Claude Code session
├── logs/                  ← one file per day /synthmem ran
└── archives/              ← weekly + monthly rollups
```

Subdirectories are created **lazily** — only when there is real content to put inside.

## File types

| Prefix | Location | What it is |
|---|---|---|
| `node_*` | root | A consolidated concept, technique, or doctrine. |
| `entity_*` | root | A person, tool, project, library, or other named thing. |
| `chat_*` | `chats/` | One per Claude Code session — distilled summary, not the raw transcript. |
| `log_*` | `logs/` | One per day on which `/synthmem` ran. |
| `_archive_*` | `archives/` | Weekly + monthly snapshots. Originals retained. |
| `_INDEX.md` | root | Full vault inventory, auto-generated. |
| `_RECENT.md` | root | Last ~14 days, auto-generated. |
| `_state.json` | root | Machine state (last-run timestamp, etc.). |
| `README.md` | root | This file. Edit freely; the skill never overwrites it. |

## Frontmatter

Every `.md` file (except `_state.json` and this README) starts with YAML frontmatter:

```yaml
---
id: YYYYMMDD-HHMMSS-xxx
type: node | entity | log | chat | archive
title: "..."
slug: kebab-case
tags: [domain1, domain2, domain3, content-type, project]
status: active | draft | deprecated | superseded
linked_nodes: ["[[node_x]]", ...]
sources: [...]
created: ISO8601
last_updated: ISO8601
---
```

Five tags exactly: 3 specific-domain + 1 content-type + 1 project-context. See the skill docs for the full taxonomy.

## Wikilinks

Use **basenames only** — never include the subdirectory:

- ✅ `[[chat_20260514_abc]]`
- ❌ `[[chats/chat_20260514_abc]]`

This way links survive if a file moves between root and a subdir.

## What the skill will and won't do

✅ Will:
- Create and append `node_*`, `entity_*`, `chats/chat_*`, `logs/log_*`.
- Maintain `_INDEX.md`, `_RECENT.md`, `_state.json`.
- Create `chats/`, `logs/`, `archives/` lazily on first need.
- Propose a new subdirectory only when ≥ 20 files of a distinct type accumulate.
- Generate weekly + monthly `_archive_*` files in `archives/` (originals preserved).
- Resolve bidirectional wikilinks.

❌ Won't:
- Delete any file.
- Modify `.git/`, `.gitignore`, `.gitattributes`, `.obsidian/`, this README, or anything in `.gitignore`.
- Touch binaries (images, PDFs, etc.) — only reference them.
- Move files the user placed by hand.
- Create speculative subdirectories.
- Make network calls.

## Backup

This vault is plain text. Back it up however you back up text: `tar`, `rsync`, `git`, Dropbox, Syncthing — your call. If you version it with `git`, the skill respects `.git/` and never writes there.
