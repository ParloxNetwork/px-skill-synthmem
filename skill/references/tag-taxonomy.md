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

This position identifies the project, client, or life context the content belongs to. Pulled from `_local/config.json` (`default_project_tag`) or inferred from the session.

Examples:
- `sermon-prep`
- `synthmem-dev`
- `client-acme`
- `personal`
- `health`
- `family`

Should be kebab-case. The user's `_local/taxonomy.overrides.md` may pin a list of allowed values — respect it if present.

## When the AI is unsure

1. Check `_INDEX.md` — what tags already exist in this domain? Reuse them if accurate.
2. Check `_local/taxonomy.overrides.md` if present.
3. If still unsure, lean specific. The indexer can roll up; it can't drill down.
4. Never invent a tag like `general`, `misc`, `other`, `stuff`, `unknown`. If you need that, you haven't understood the content yet — re-read.

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

A daily log:
```yaml
tags:
  - daily-log
  - synthmem-dev
  - meta
  - summary
  - synthmem-dev
```
(Yes, project tag may repeat in position 1 when the log is project-specific. That's expected.)
