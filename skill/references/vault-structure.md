# Vault structure

The vault is a **hybrid Markdown layout**: the semantic core lives at the root, high-cardinality transient files live in subdirectories. Optimized for both AI navigation and Obsidian graph view.

## Layout

```
vault-root/
├── README.md            (user-editable; the skill never overwrites)
├── _INDEX.md            (auto-generated inventory)
├── _RECENT.md           (auto-generated last 14 days)
├── _state.json          (machine state — last_run, counters, errors)
├── node_*.md            (atomic concepts — your semantic vocabulary)
├── entity_*.md          (people, tools, projects, AIs, datasets)
├── chats/               (created lazily on first chat write)
│   └── chat_YYYYMMDD_<id>.md
├── logs/                (created lazily on first log write)
│   └── log_YYYYMMDD.md
└── archives/            (created lazily on first compaction)
    └── _archive_YYYY-MM.md
```

## File prefixes

| Prefix | Where it lives | Purpose |
|---|---|---|
| `node_` | root | A consolidated concept, doctrine, technique. Atomic unit of knowledge. |
| `entity_` | root | A named thing: person, tool, project, AI, organization, dataset. |
| `chat_` | `chats/` | One per Claude Code session — a distilled summary, not the raw transcript. |
| `log_` | `logs/` | One per day on which `/synthmem` ran. Run report + pointers to its work. |
| `_archive_` | `archives/` | Weekly (`_archive_YYYY-WW.md`) or monthly (`_archive_YYYY-MM.md`) rollups. |
| `_INDEX.md`, `_RECENT.md`, `_state.json`, `README.md` | root | Meta — always at the root for predictable bootstrapping. |

## Why hybrid (not fully flat, not deeply nested)

- **Root stays scannable.** `node_*` and `entity_*` form your knowledge vocabulary; you want them visible at a glance in Obsidian's file pane or `ls`.
- **High-cardinality types are quarantined.** An active user produces ~1 chat per session and 1 log per day. Without subdirs the root drowns within months.
- **Compaction is semantically clean.** Moving a `log_*` from `logs/` into `archives/_archive_*.md` is intuitive; moving between two root-level prefixes is not.
- **Wikilinks survive the layout.** Obsidian resolves `[[chat_20260514_abc]]` by basename regardless of subdirectory, so links written before any restructuring keep working.

## Lazy directory creation (strict YAGNI)

The skill does NOT pre-create `chats/`, `logs/`, or `archives/` at init time. They come into existence the first time the skill has a real file to place there:

- `chats/` is created the first time a `chat_*.md` is written.
- `logs/` is created the first time a `log_*.md` is written.
- `archives/` is created the first time compaction needs to write an `_archive_*.md`.

A freshly initialized vault that has never been run looks like:

```
vault-root/
├── README.md
├── _INDEX.md
├── _RECENT.md
└── _state.json
```

…and grows organically as content actually arrives.

## Creating new subdirectories — the YAGNI rule

The 3 standard subdirectories (`chats/`, `logs/`, `archives/`) are the only ones the skill is allowed to create automatically.

The skill MAY propose a new subdirectory only when **all** of these hold:

1. A clearly distinct file-type category has emerged in real use.
2. That category has accumulated **≥ 20 files** of its own type at the root.
3. Keeping them at the root would visibly degrade navigation (the user has flagged it, OR the AI has documented the pattern in two prior run reports).

*Would* justify a new bucket:
- `decisions/` — if `decision-*` files accumulate beyond 20.
- `recipes/` — same threshold, same logic.

*Would not* justify it:
- A handful of edge-case files (< 20). Leave them at the root.
- Speculation about what might be useful later. Don't preempt.

When the skill creates a new bucket, it must:
- Note the creation in the next run report (in `log_*.md`).
- Add a one-line entry under a "Custom buckets" section in `_INDEX.md`.
- Move existing same-type files into the new bucket in the same run.

If the user later prefers a different layout, they `mv` files manually; the skill respects user-made moves on subsequent runs (it does not re-shuffle them).

## Wikilinks across subdirectories

Wikilinks use **basenames** without subdirectory prefixes:

- ✅ `[[chat_20260514_abc]]`
- ✅ `[[node_soteriology]]`
- ❌ `[[chats/chat_20260514_abc]]` (works in Obsidian, but breaks if the file moves)

The linker sub-agent strips any subdirectory prefix found in `linked_nodes` arrays and warns. This guarantees portability if a file moves between root and a subdir.

If two files in different subdirs share a basename, the second to be written is renamed with a numeric suffix (e.g., `chat_20260514_abc-2.md`). Slug collisions are rare given the timestamp + random-suffix scheme.

## Underscore-prefix convention

Files starting with `_` are infrastructure or rollups:
- Sort to the top of alphabetical listings (`_INDEX.md`, `_RECENT.md`, `_archive_*.md`).
- Visually mark "not content".

Inside `archives/`, the `_archive_` prefix is kept for the same readability reason.

## Slug rules

The portion of the filename after the prefix must be:

- `kebab-case` (lowercase, hyphens, no spaces).
- ASCII only (no accents — keeps grep portable).
- ≤ 50 characters.
- No leading / trailing hyphens.

Examples:
- ✅ `node_soteriology.md`
- ✅ `chats/chat_20260514_a1b2.md`
- ✅ `logs/log_20260514.md`
- ❌ `node_Soteriología.md` (accent + capital)
- ❌ `node_what_i_learned.md` (snake_case)

## ID collision rule

Frontmatter `id` is `YYYYMMDD-HHMMSS-xxx` where `xxx` is a 3-char base36 random suffix. The suffix prevents collisions when sub-agents write within the same second.

## Off-limits — the skill never writes to these

- `.git/`, `.gitignore`, `.gitattributes`
- `.obsidian/` and any other tool's config directory
- Any file matching the vault's own `.gitignore` patterns
- Any file the user marked with `user_edited: true` in its frontmatter, or wrote below a `## User notes` heading
- Subdirectories the user created by hand (the skill never moves user-placed files)

## What never appears in the vault

- Binary files (images, audio, video, PDFs, office docs). Only references plus AI-written descriptions.
- Files without YAML frontmatter (except `_state.json` and `README.md`).
- Files outside the prefix system written by the skill (user-created files are left alone).
- Personal paths or identifiers that should live in `_local/config.json` instead.

## File lifecycle

```
Session happens                        (Claude Code stores JSONL)
        ↓
/synthmem run                          (this skill)
        ↓
chats/chat_YYYYMMDD_<id>.md created    (distilled summary)
        ↓
Concepts and entities extracted        → node_*.md, entity_*.md (root, create or append)
        ↓
Wikilinks resolved (bidirectional)     → both ends updated
        ↓
logs/log_YYYYMMDD.md updated           (run report appended)
_RECENT.md regenerated                 (last 14 days)
_INDEX.md regenerated                  (full inventory)
_state.json bumped                     (last_run, per-day progress)
        ↓
Compaction check                       → if due, write archives/_archive_*.md
                                          and stub-rename the source files in place.
                                          Originals are never deleted.
```
