# Vault structure

The vault is a **hybrid Markdown layout**: the semantic core lives at the root, high-cardinality transient files live in subdirectories. Optimized for both AI navigation and Obsidian graph view.

## Layout

```
vault-root/
├── README.md            (user-editable; the skill never overwrites)
├── _INDEX.md            (auto-generated inventory)
├── _RECENT.md           (auto-generated last 14 days)
├── _state.json          (machine state — last_run, counters, errors)
├── nodes/               (created lazily on first node write)
│   └── node_*.md        (atomic concepts — your semantic vocabulary)
├── entities/            (created lazily on first entity write)
│   └── entity_*.md      (people, tools, projects, AIs, datasets)
├── chats/               (created lazily on first chat write)
│   └── chat_YYYYMMDD_<id>.md
├── logs/                (created lazily on first log write)
│   └── log_YYYYMMDD.md
└── archives/            (created lazily on first compaction)
    └── _archive_YYYY-MM.md
```

The **root contains only meta files** (README + 3 `_*` files). All content lives in typed subdirectories, each created lazily on first write.

## File prefixes

| Prefix | Where it lives | Purpose |
|---|---|---|
| `node_` | `nodes/` | A consolidated concept, doctrine, technique. Atomic unit of knowledge. |
| `entity_` | `entities/` | A named thing: person, tool, project, AI, organization, dataset. |
| `chat_` | `chats/` | One per Claude Code session — a distilled summary, not the raw transcript. |
| `log_` | `logs/` | One per day on which `/synthmem` ran. Run report + pointers to its work. |
| `_archive_` | `archives/` | Weekly (`_archive_YYYY-WW.md`) or monthly (`_archive_YYYY-MM.md`) rollups. |
| `_INDEX.md`, `_RECENT.md`, `_state.json`, `README.md` | root | Meta — always at the root for predictable bootstrapping. |

## Why each type in its own subdirectory

- **Root stays truly clean.** Only 4 meta files at root (README, _INDEX, _RECENT, _state.json). Opening the vault, the user sees structure, not content noise. v0.5/v0.6.0 kept `node_*` and `entity_*` at root but a single active day produces 30+ of them — the "scannable root" promise broke. v0.6.1 fixes this by typing everything.
- **Each subdirectory has a single semantic purpose.** No mixed-type clutter.
- **Compaction is semantically clean.** Moving a `log_*` from `logs/` into `archives/_archive_*.md` is intuitive.
- **Wikilinks survive layout changes.** Obsidian resolves `[[chat_20260514_abc]]` by basename regardless of subdirectory, so links written before any restructuring keep working.

## Lazy directory creation (strict YAGNI)

The skill does NOT pre-create any subdirectory at init time. Each comes into existence the first time the skill has a real file to place there:

- `nodes/` is created the first time a `node_*.md` is written.
- `entities/` is created the first time an `entity_*.md` is written.
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

## Migrating a pre-v0.6.1 vault

If a vault from v0.5/v0.6.0 has `node_*.md` and `entity_*.md` at the root, the indexer on its first v0.6.1 run **must**:

1. Create `nodes/` and `entities/` if missing.
2. `mv` every root-level `node_*.md` → `nodes/`.
3. `mv` every root-level `entity_*.md` → `entities/`.
4. Set `migrated_to_typed_subdirs: true` in `_state.json` so subsequent runs skip the check.
5. Record the migration in the run report.

Wikilinks (which use basenames) keep resolving — no link updates needed.

## Creating new subdirectories — the YAGNI rule (autonomous)

The 3 standard subdirectories (`chats/`, `logs/`, `archives/`) are the standard set the skill creates lazily on first use.

The skill MAY **autonomously create** a new subdirectory when:

1. A distinct filename-prefix pattern has emerged at the root.
2. That pattern has accumulated **≥ 20 files** matching `<prefix>-*.md` or `<prefix>_*.md`.
3. The prefix is not one of `node`, `entity`, `log`, `chat`, or an underscore-prefixed meta name.

Detection is cheap (one bash invocation during indexing):

```bash
# Look at the root for anything that isn't a meta file (README, _*.md).
# Standard typed files (node_*, entity_*, chat_*, log_*) already live in subdirs.
ls "$VAULT_PATH"/*.md 2>/dev/null \
  | xargs -n1 basename \
  | grep -vE '^(README|_)' \
  | sed -E 's/^([a-z0-9]+)[-_].*/\1/' \
  | sort | uniq -c | awk '$1 >= 20 {print $2, $1}'
```

When the threshold is crossed for prefix `<p>`, the skill **in the same run**:

1. Creates the directory `<p>s/` (plural — `decision` → `decisions/`, `recipe` → `recipes/`).
2. Moves all matching `<p>-*.md` and `<p>_*.md` files into it.
3. Adds a one-line entry under a "Custom buckets" section in `_INDEX.md`.
4. Records the bucket creation in today's `logs/log_YYYYMMDD.md` under `## 🪣 Buckets auto-created`:

   ```markdown
   ## 🪣 Buckets auto-created
   - `decisions/` (23 `decision-*` files moved in)
     Rationale: prefix pattern crossed the 20-file YAGNI threshold.
   ```

### Safety bounds on autonomous creation

- **Max one new bucket per run.** Avoids surprise reorganization.
- **Move only — never delete.** Wikilinks survive because they use basenames.
- **Respect user moves.** If the user has `mv`ed a file by hand into or out of a bucket, the skill does not re-shuffle it on subsequent runs.
- **Never re-create a bucket the user explicitly removed** (heuristic: if the directory was deleted and its files manually placed back at the root, do not re-create — log a warning instead).

If the user disagrees with a bucket the skill created, they `mv` the files back and `rmdir` the empty directory. Next run notices the move and respects it.

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

**Canonical rule (the validator enforces this):** the frontmatter `slug` MUST equal the filename stem with the type prefix stripped, **verbatim**.

- `nodes/node_soteriology.md` → slug `soteriology`
- `chats/chat_20260514_a1b2.md` → slug `20260514_a1b2`
- `logs/log_20260514.md` → slug `20260514`
- `archives/_archive_2026-W16.md` → slug `2026-W16`
- `_INDEX.md` / `_RECENT.md` → slug `INDEX` / `RECENT` (meta files; case-insensitive)

This guarantees slug ↔ filename consistency by construction and eliminates an entire class of validator warnings.

### Semantic slugs (node_ / entity_)

For knowledge files the slug is author-chosen and must be:
- `kebab-case` (lowercase, hyphens, no spaces).
- ASCII only (no accents — keeps grep portable).
- ≤ 50 characters.
- No leading / trailing hyphens.

✅ `node_soteriology.md`, `entity_claude-code.md`
❌ `node_Soteriología.md` (accent + capital), `node_what_i_learned.md` (snake_case)

### Time-keyed slugs (chat_ / log_ / _archive_)

These are **not** kebab-case — they are date/id forms and may contain `_` and uppercase (`2026-W16`). They are exempt from the kebab-only rule because the filename tail *is* the slug. What matters is that `slug` == filename-tail exactly.

✅ `chat_20260514_a1b2.md` slug `20260514_a1b2`
✅ `_archive_2026-W16.md` slug `2026-W16`
❌ `chat_20260514_a1b2.md` slug `20260514-a1b2` (hyphen ≠ filename's underscore)

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
Concepts and entities extracted        → nodes/node_*.md, entities/entity_*.md (create or append)
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
