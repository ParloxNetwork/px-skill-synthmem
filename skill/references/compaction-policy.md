# Compaction policy

**Nothing is ever deleted.** Compaction is *reorganization with provenance*, never destruction.

The vault is meant to grow indefinitely. Markdown is cheap (a year of daily logs is well under 50 MB). The goal of compaction is not to save space — it is to keep the *active surface* of the vault navigable, while preserving every word elsewhere.

## What gets compacted

Only **time-keyed** files: `logs/log_YYYYMMDD.md` and `chats/chat_YYYYMMDD_*.md`.

`node_*` and `entity_*` are evergreen — they are appended to over time, never compacted. (The user may manually refactor them; the skill won't.)

## Cadence

The user runs `/synthmem` roughly 3–5 times a week (their stated rhythm). Compaction therefore runs **at the end of every `/synthmem` invocation**, but only does work when thresholds are crossed.

### Weekly snapshot — after 7 days

For each ISO week that ended **more than 7 days ago** and has any `log_*` / `chat_*` files in it:

1. Create `archives/` if it does not yet exist (lazy creation — first compaction triggers it).
2. Create or open `archives/_archive_YYYY-WW.md` (`YYYY-WW` = ISO year-week, e.g. `2026-W19`).
3. For each `logs/log_YYYYMMDD.md` in that week, append a section to the archive:
   ```markdown
   ## log_20260514 — 2026-05-14

   <full content of the log, verbatim>

   _Original file: [[log_20260514]]_
   ```
4. For each `chats/chat_*.md` in that week, append similarly (full distilled summary, not the raw transcript — the chat file already only holds a summary).
5. **Do not delete the original files.** They stay in `logs/` and `chats/`.
6. Add the new `_archive_*` to `linked_nodes` in each original (`linked_nodes: ["[[_archive_2026-W19]]"]`).

After this, the originals are "snapshotted" — present in two places. The cost is negligible.

### Monthly roll-up — after 30 days

For each calendar month that ended **more than 30 days ago**:

1. Create or open `archives/_archive_YYYY-MM.md` (e.g. `_archive_2026-05.md`).
2. For each `archives/_archive_YYYY-WW.md` in that month, append its content as a section.
3. **Do not delete the weekly archives.** They stay.

The monthly archive is a single-file, scrollable view of "what happened in May 2026" — convenient for the user, navigable by Claude.

### Yearly roll-up — after 365 days (v0.6+)

Not implemented in v0.5. Will roll monthly into yearly archives, same pattern.

## What compaction never does

- Never deletes `log_*`, `chat_*`, `node_*`, `entity_*`, `_INDEX.md`, `_RECENT.md`, `_state.json`, or any file the user authored.
- Never modifies content of an existing file beyond appending. The only fields it may bump in old files are `last_updated` and `linked_nodes`.
- Never compacts files newer than the threshold (7 days for weekly, 30 days for monthly).
- Never compacts `node_*` or `entity_*` — they are not time-keyed.
- Never touches files in `.gitignore`.
- Never alters `.git/` or `.obsidian/`.
- Never moves files the user placed by hand.

## Why "snapshot, don't move"

Because:

1. **Catastrophic recoverability.** If an archive file is corrupted, the originals still exist.
2. **Wikilink stability.** A wikilink `[[log_20260514]]` from any node continues to resolve, regardless of which directory holds the file.
3. **User trust.** The user explicitly does not want information loss. Compaction must not feel like deletion.

The duplication cost is tiny (raw text), and it is the price of safety.

## `_RECENT.md`

`_RECENT.md` is the only file that *prunes* — but it never holds primary content. It is purely a navigational summary of the last ~14 days:

- Entries older than 14 days are dropped from `_RECENT.md`.
- The originals (`logs/log_*`, `chats/chat_*`) are untouched.
- So `_RECENT.md` is regenerable at any time from the vault contents.

## What the user sees at the file-system level

After a year of active use:

```
my-synth-vault/
├── README.md
├── _INDEX.md
├── _RECENT.md
├── _state.json
├── node_*.md                   ← evergreen, no time-based compaction
├── entity_*.md                 ← evergreen, no time-based compaction
├── chats/
│   ├── chat_20260101_a1b2.md   ← every chat reference, kept
│   ├── chat_20260102_c3d4.md
│   └── ... (one per session you had)
├── logs/
│   ├── log_20260101.md         ← every log, kept
│   ├── log_20260102.md
│   └── ... (one per day you ran /synthmem)
└── archives/
    ├── _archive_2026-W01.md    ← weekly snapshots
    ├── _archive_2026-W02.md
    ├── ... (52 weekly archives)
    ├── _archive_2026-01.md     ← monthly roll-ups
    └── ... (12 monthly archives)
```

It looks "busy" inside the subdirectories, but `_INDEX.md` and `_RECENT.md` (at the root) give you the navigable view. Obsidian's file pane and graph view stay focused on `node_*` and `entity_*` unless you explicitly browse into a subdirectory.
