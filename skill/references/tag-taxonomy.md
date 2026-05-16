# Tag taxonomy

Every file has **exactly 5 tags** in a fixed order:

| Position | Role | Count | Examples |
|---|---|---|---|
| 1–3 | **Domain** | 3 | `soteriology`, `homiletics`, `python`, `react`, `prompt-engineering` |
| 4 | **Content type** | 1 | `concept`, `pattern`, `decision`, `recipe`, `reference`, `entity`, `summary`, `meta` |
| 5 | **Project context** | 1 | `sermon-prep`, `synthmem-dev`, `client-acme`, `personal` |

Total: 5.

## Why the strict shape

- **Predictable indexing.** The `indexer` sub-agent groups files by position-1 (primary domain), filters by position-4 (e.g., "all decisions"), and pivots by position-5 (e.g., "everything from project X"). If tags are free-form, this falls apart.
- **Searchable from outside the skill.** `grep '^- sermon-prep$'` on the `tags:` block works.
- **Forces specificity.** Five is enough to be expressive, few enough that the AI must choose carefully.

## Assignment ORDER — resolve 5 → 4 → 3, never the reverse

A v0.6.1 bug: the AI picked the 3 domain tags first, then often repeated one of them in the project (5) or content-type (4) slot — e.g. `[teologia-sistematica, atributos-de-dios, homiletics, reference, teologia]` where position 5 (`teologia`) is just a generic echo of position 1, not a project. Or `[synthmem-dev, …, …, concept, synthmem-dev]` with position 1 == position 5.

To prevent this, resolve tags in **reverse order of constraint**:

1. **Position 5 — project context — FIRST.** Pick the real project/life context. Source priority:
   - An explicit project signal in the session (working dir, repo name, "this is for the sermon", etc.).
   - Else `config.default_project_tag`.
   - Recurring real-world activity (e.g. sermon/homiletic prep, a client engagement, a hobby project) → a *context* tag for that activity such as `sermon-prep` or `<your-congregation-slug>`, **never** the topic word (`teologia`, `theology`). Treat ongoing ministry/work/study as a real project, not a subject. (User-specific contexts — congregation name, client names — belong in `_local/`, never hardcoded here.)
   - A project tag is a *context*, never a *topic*. `synthmem-dev`, `sermon-prep`, `infra`, `client-x`, `personal` — yes. `theology`, `python`, `markdown` — no.

2. **Position 4 — content-type — SECOND.** Exactly one from the fixed vocabulary (see below).

3. **Positions 1–3 — domain — LAST.** Pick the 3 most specific domain tags **that are not already used in position 4 or 5**. If a strong domain candidate collides with the project or content-type tag, drop it and take the next-best specific tag.

**Distinctness invariant:** all 5 tags MUST be unique. No tag may appear twice across the five positions. If after selection a collision remains, the domain tags (picked last, most fungible) yield — never the project or content-type.

## Specificity rule — read this carefully

**Prefer the most specific accurate tag.** Do not default to umbrella terms.

| Generic (avoid) | Specific (prefer) |
|---|---|
| `theology` | `soteriology`, `eschatology`, `christology`, `pneumatology` |
| `programming` | `python`, `typescript`, `bash`, `rust` |
| `ai` | `claude-code`, `mcp`, `prompt-engineering`, `rag` |
| `writing` | `homiletics`, `technical-writing`, `copy` |
| `tools` | `obsidian`, `git`, `docker` |

If a concept genuinely spans multiple specific tags, use 2 or 3 of them — that's what position 1, 2, 3 are for.

If the concept truly is at the umbrella level (a meta-discussion *about* theology as a field, not within it), then `theology` is the right tag. But that is rare.

## Position 1 vs 2 vs 3 in the domain block

There is no rigid hierarchy, but a soft convention:
- Position 1 = primary domain (the field the file most "belongs to").
- Position 2 = secondary domain (closely related).
- Position 3 = tertiary / cross-cutting (a method, era, school, sub-area).

The indexer groups files by position 1, so put the most important tag first.

## Content-type tags (position 4) — fixed vocabulary

Exactly one of:

| Tag | Use when the file is... |
|---|---|
| `concept` | An abstract idea, definition, doctrine, term. |
| `pattern` | A reusable solution, technique, code pattern, mental model. |
| `decision` | A choice with rationale (architectural, life, project). |
| `recipe` | Step-by-step instructions for a concrete outcome. |
| `reference` | External material distilled (paper, talk, book chapter). |
| `entity` | A person, tool, project (use only on `entity_*` files). |
| `summary` | A roll-up of multiple sessions/topics (use on `log_*`, `chat_*`, `_archive_*`). |
| `meta` | Vault infrastructure (`_INDEX.md`, `_RECENT.md`, etc.). |

If you find yourself wanting to introduce a new content-type tag, **don't** — first try to fit one of these. Adding new ones requires updating this file.

## Project-context tags (position 5) — extensible

This position identifies the **project / client / life context** — never a topic. Resolved FIRST (see "Assignment ORDER" above). Pulled from a session project signal, else `config.default_project_tag`.

Valid (contexts) — examples, adapt to your own life/work:
- `sermon-prep` / `<your-congregation-slug>` — recurring ministry work
- `synthmem-dev` — work on this skill
- `infra` — server / tooling / migrations
- `client-acme` — a specific client engagement
- `personal`, `health`, `family` — life contexts

> Concrete personal contexts (real congregation, client, or family names) are configured per-user in `_local/`, never written into this public spec.

Invalid here (these are domains, not projects — they belong in positions 1–3):
- ❌ `theology`, `teologia`, `python`, `markdown`, `claude-code`

Should be kebab-case. The user's `_local/taxonomy.overrides.md` may pin a list of allowed values — respect it if present. If you cannot identify a real project context, use `config.default_project_tag`; do not echo a domain tag here.

## When the AI is unsure

1. Check `_INDEX.md` — what tags already exist in this domain? Reuse them if accurate.
2. Check `_local/taxonomy.overrides.md` if present.
3. If still unsure, lean specific. The indexer can roll up; it can't drill down.
4. Never invent a tag like `general`, `misc`, `other`, `stuff`, `unknown`. If you need that, you haven't understood the content yet — re-read.

## Genericity lint (v0.6.10)

`validate_vault.py` runs a deterministic advisory check: an umbrella / placeholder term used in a **domain slot** (positions 1–3) is flagged. It is a **warning, never an error** — genericity is a semantic judgement, so it never blocks the gate, never triggers auto-repair, and is surfaced in the day's log `## Para revisar (opcional)`. Fixing it requires a human/distiller semantic re-tag.

**Canonical denylist** (single source of truth — `validate_vault.py` `GENERIC_DOMAIN_TAGS` is kept in sync with this list):

```
general, misc, miscellaneous, other, stuff, unknown, notes,
tech, technology, theology, programming, coding, ai, writing,
tools, tooling, software, development, vault-meta, unfiled
```

- `unfiled` is **exempt on `status: draft` files** — it is the intentional, temporary placeholder a ≥3-ref stub carries until the distiller fleshes it out.
- Specific replacements: `theology` → `soteriology`/`christology`/…; `programming` → `python`/`bash`/…; `ai` → `claude-code`/`mcp`/…; `tools` → `obsidian`/`git`/… (see "Specificity rule" above).

**Not done — and why**: a "vocabulary drift" heuristic (flag a tag that is the token-prefix of ≥3 other vault tags) was prototyped and dropped. It false-positived on legitimate hierarchical tags — `claude-code` is a *good* specific tag yet looks like an "umbrella" of `claude-code-skills`, `claude-code-memory`, … A stdlib script can't tell a parent tag from a too-generic one without semantic understanding, and a noisy advisory that cries wolf is worse than a precise one. The denylist stays the only signal.

## Examples

A sermon outline on the doctrine of justification:
```yaml
tags:
  - justification
  - soteriology
  - reformed-theology
  - concept
  - sermon-prep
```

A code pattern for Claude Code skill structure:
```yaml
tags:
  - claude-code
  - skill-design
  - prompt-engineering
  - pattern
  - synthmem-dev
```

A decision to use Dropbox sync over git:
```yaml
tags:
  - vault-management
  - sync-strategy
  - data-resilience
  - decision
  - synthmem-dev
```

A daily log (note: all 5 tags distinct — the project tag appears ONLY in position 5):
```yaml
tags:
  - daily-log
  - knowledge-management
  - vault-ops
  - summary
  - synthmem-dev
```
The distinctness invariant applies to **every** file type, logs included. A log's domain tags (positions 1–3) describe what the run was about (`daily-log` plus the run's dominant themes); position 4 is always `summary`; position 5 is the project context. Never repeat the project tag in a domain slot.
