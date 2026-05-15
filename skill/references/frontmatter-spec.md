# Frontmatter specification

Every file in the vault (except `_state.json` and `README.md`) begins with a YAML frontmatter block. No exceptions.

## Schema

```yaml
---
id: YYYYMMDD-HHMMSS-xxx          # required. xxx = 3-char base36 random suffix.
type: node | entity | log | chat | archive  # required.
title: "Human-readable title"     # required. Free text, can use accents.
slug: my-concept-slug             # required. Matches the filename after the prefix.
tags:                             # required. Exactly 5, see tag-taxonomy.md.
  - domain1
  - domain2
  - domain3
  - content-type
  - project-context
status: active | draft | deprecated | superseded   # required. Default: active.
linked_nodes:                     # optional but encouraged. Bidirectional wikilinks.
  - "[[node_other-concept]]"
  - "[[entity_some-tool]]"
sources:                          # optional. Where this content came from.
  - chat: "[[chat_20260514_a1b2]]"
  - log: "[[log_20260514]]"
  - external: "https://example.com/article"
created: 2026-05-14T10:23:00-05:00   # required. ISO 8601 with timezone.
last_updated: 2026-05-14T22:11:00-05:00   # required. ISO 8601 with timezone.
superseded_by: "[[node_better-version]]"  # required only if status == superseded.
---
```

## Field-by-field

### `id` (required, immutable once set)

Format: `YYYYMMDD-HHMMSS-xxx`.

- `YYYYMMDD-HHMMSS` is the file's creation timestamp in vault timezone.
- `xxx` is a 3-character base36 random suffix (`0-9a-z`), chosen at creation.

Why the suffix: when multiple sub-agents write within the same second, plain timestamps collide silently. The suffix makes collisions astronomically unlikely.

Never change `id` after creation, even if you rename or refactor the file.

### `type` (required)

One of:
- `node` — a knowledge atom
- `entity` — a named thing
- `log` — a daily log
- `chat` — a session reference
- `archive` — a weekly/monthly archive
- `meta` — vault infrastructure files (`_INDEX.md`, `_RECENT.md`)

Must match the file's prefix (`node_*.md` → `type: node`, `_INDEX.md` → `type: meta`).

### `title` (required)

Free-form, human-readable. May contain accents, punctuation, emoji. This is what shows up in indexes and graph view labels.

### `slug` (required)

The kebab-case identifier used in the filename and wikilinks. Must match the part after the prefix.

If the file is `node_soteriology.md`, the slug is `soteriology`.

### `tags` (required — exactly 5)

The taxonomy is strict. See `tag-taxonomy.md`. Positions 1-3 are domain, position 4 is content-type, position 5 is project.

**Resolve in the order 5 → 4 → 3** (project first, content-type second, domain last) and enforce the **distinctness invariant**: all 5 tags must be unique — no value may repeat across positions. Position 5 is a project/life *context* (`sermon-prep`, `synthmem-dev`, `infra`), never a topic word. The indexer relies on this ordering and on tags being distinct.

If a file genuinely doesn't have a domain (rare — usually meta files), use the placeholder `meta`.

### `status` (required)

- `active` — the current canonical version. Default.
- `draft` — still being shaped, may be incomplete.
- `deprecated` — kept for history but the concept is no longer recommended/used.
- `superseded` — replaced by another file. Requires `superseded_by` field.

### `linked_nodes` (optional but expected)

Array of wikilinks. Maintained **bidirectionally**: if A links to B, B should link back to A. The `linker` sub-agent enforces this.

Format: each item is a wikilink string like `"[[node_x]]"`. Quote them; YAML otherwise misreads `[[ ]]`.

### `sources` (optional)

Where this content came from. Three kinds:
- `chat:` — a session reference inside the vault
- `log:` — a daily log inside the vault
- `external:` — anything outside the vault (URL, book, paper)

Lets the user trace any claim back to its provenance.

### `created`, `last_updated` (required)

ISO 8601 with timezone offset. Use the vault's configured timezone.

`created` is set once and never changed.
`last_updated` bumps every time the file is touched.

### `superseded_by` (conditional)

Required iff `status == superseded`. A single wikilink to the replacement.

## Forbidden frontmatter patterns

- Empty `tags` array. Always 5 tags.
- `id` reused across files.
- `title` identical to `slug`. The title should be human, the slug machine.
- Timestamps in UTC without offset when the rest of the vault is local.
- `linked_nodes` pointing at non-existent files (the `linker` sub-agent removes stale links and warns).

## Minimal example

```yaml
---
id: 20260514-223011-k7q
type: node
title: "Doctrine of soteriology"
slug: soteriology
tags:
  - soteriology
  - reformed-theology
  - grace
  - concept
  - sermon-prep
status: active
linked_nodes:
  - "[[node_justification]]"
  - "[[node_sanctification]]"
  - "[[entity_calvin]]"
sources:
  - chat: "[[chat_20260514_a1b2]]"
created: 2026-05-14T22:30:11-05:00
last_updated: 2026-05-14T22:30:11-05:00
---
```

## Markdown-safe output (applies to ALL generated files)

The vault is read in Obsidian, VS Code, GitHub, plain `cat` — the content must not break any Markdown renderer. The most common breakage (found in v0.6.1 testing) is a bare angle-bracket placeholder like `<proj>` in a path: renderers treat it as an unclosed HTML tag and **silently swallow everything after it**, including later headings and list items. One bad `_INDEX.md` line destroyed the whole rest of the file's rendering.

Rules for every generated file (`_INDEX.md`, `_RECENT.md`, `node_*`, `entity_*`, `log_*`, `chat_*`, `_archive_*`):

1. **Backtick anything code-ish.** Paths, placeholders, env vars, shell commands, generics:
   - ✅ `` `~/.claude/projects/<proj>/` ``
   - ✅ `` `<session-id>` ``
   - ❌ `~/.claude/projects/<proj>/` (bare — breaks the renderer)
2. **If it's prose, escape.** When backticks would be semantically wrong, use `&lt;` / `&gt;`.
3. **One-line descriptions in `_INDEX.md` / `_RECENT.md`** must be backtick-safe: scan the description for `<`, `>`, unescaped `|`, and leading `#`; wrap or escape before writing the line.
4. **Pipes in tables.** A literal `|` inside a table cell must be `\|` or backticked.
5. **Leading `#` that is not a heading** (e.g. a comment, a CSS id) must be backticked or indented, or the renderer turns it into an `<h1>`.
6. **Wikilinks are exempt** — `[[...]]` is not affected by this; never backtick a wikilink (that would disable it).

The indexer and every writing sub-agent must apply this as a final pass before writing a file. Treat it as part of "the file is valid", same level as "the frontmatter parses".
