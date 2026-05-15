---
name: synthmem
description: Consolidate Claude Code sessions into a persistent, plain-Markdown "synthetic memory" vault. Use this whenever the user runs `/synthmem`, asks to "consolidate today", wants to "save what we did to the vault", references their "third brain" or "synth vault", asks to archive sessions, or wants to extract concepts/entities from recent conversations into a long-term Obsidian-compatible store. Trigger even if the user does not say "synthmem" by name, as long as the intent is to write Claude session content into a durable Markdown vault.
---

# synthmem

You are operating the **synthmem skill**: a batch consolidator that turns Claude Code sessions into a durable, plain-Markdown vault. The user has invoked you because they want recent conversational work captured, organized, linked, and archived — not to chat.

## What you are doing

When invoked you:

1. Resolve **configuration** from `_local/config.json` using the strict path-resolution algorithm in `references/privacy-and-config.md`. The config lives next to the skill repo (resolved via `readlink -f ~/.claude/skills/synthmem`), **not** in the current working directory. If missing, abort and tell the user which paths were searched. Never invent paths.
2. Resolve the **time window**: read `_state.json` in the vault to find `last_run`, then process every Claude Code session between `last_run` and "now". If `_state.json` is missing, run the **first-run flow** (see `references/catch-up-logic.md`) — that is the only place you ask the user a question.
3. **Harvest** raw session transcripts from the configured `claude_sessions_dir`. See `references/session-source.md`.
4. **Distill** concepts, entities, decisions, and code patterns from those transcripts into typed Markdown files: `node_*` in `nodes/`, `entity_*` in `entities/`, `chat_*` in `chats/`, `log_*` in `logs/`. Apply the **distiller quality bar** (see `references/multi-agent-orchestration.md`) — fragment less, merge more.
5. **Link** new and existing files bidirectionally with `[[wikilinks]]` (use basenames, never include the subdirectory prefix).
6. **Index** the vault: update `_INDEX.md` and `_RECENT.md` (both at the root).
7. **Compact** old daily logs and chats into `archives/_archive_*.md` — **without deleting** original content. See `references/compaction-policy.md`.
8. **Validate (scope-aware)**: run `scripts/validate_vault.py --vault ${VAULT_PATH} --changed <files this run wrote/touched>`. Fold the `summary` into the daily log.
9. **Auto-heal (automatic — the user never types `/synthmem repair` for routine drift)**: if validation reported **any deterministically-fixable issue** (tag distinctness, slug≠filename-tail, asymmetric wikilinks, archive content-type, markdown `<…>` hazards) — whether legacy or introduced by this run — automatically run `scripts/repair_vault.py --vault ${VAULT_PATH} --project ${PROJECT_TAG}`, then **re-run the validator**. In the log, record what repair fixed, split into:
   - **legacy** (files this run didn't touch) — expected, just note the count.
   - **in-scope** (files this run wrote) — this means the distiller/linker produced fixable output; flag it in the log as `⚠ distiller-smell: investigate` so we keep the observability signal even though the vault self-healed.
   Auto-heal is skipped entirely when validation is already clean (zero cost on healthy vaults).
10. **Finalize**: after the re-validation, finalize `_state.json` (`finalize-run`) **unless** there are still genuine in-scope ERRORs that repair could not fix (then `last_run_status: "partial"`). Non-auto-fixable **flagged** items (e.g. duplicate-domain-tags needing a semantic re-tag) **never block** — blocking would create a stuck overnight state, the opposite of autonomous.
11. **Write** the end-of-run report to `logs/log_YYYYMMDD.md`, including a `## Para revisar (opcional)` section listing any flagged items with a concrete suggested action.
12. **Tell the user** briefly what was done (verdict + counts). If flagged items exist, add **one concrete line**: e.g. *"Si tienes chance: revisa `node_x` (2 tags de dominio duplicados, decide cuál va). Si no, queda anotado en `logs/log_YYYYMMDD.md` → 'Para revisar', lo retomas cuando quieras — sin problema."* If nothing needs review, say so plainly.

### Autonomy contract (non-negotiable)

The user's expectation: type `/synthmem` at end of day, leave the machine on, come back to a **finished** state. Therefore:

- The run **always reaches a terminal state** — finalized, or `partial` with a clear logged reason. It never hangs waiting for input (the only documented prompt is first-run, and `first_run_default` removes even that).
- Vault hygiene (legacy + drift) is **self-healed automatically** via step 9. The standalone `/synthmem repair` remains for manual/debug use but is **not required** for routine operation.
- Sub-agent failures don't abort the run: mark the session pending, continue, retry next run (see `catch-up-logic.md`). A run with partial failures still finalizes the parts that succeeded and reports what's pending.
- Anything that genuinely needs human judgment is **surfaced, not blocking**: one line in the final summary + a `## Para revisar (opcional)` section in the day's log. The user reviews on their own schedule or never; the vault stays consistent either way.

### `/synthmem validate` — read-only audit mode

If invoked as `/synthmem validate`, do **only** step 8 against the existing vault: run `validate_vault.py`, print the report, exit. No harvest, no distill, no writes, no `_state.json` change. This lets the user audit a large vault cheaply without reprocessing.

### `/synthmem repair` — reconcile an existing vault

If invoked as `/synthmem repair`, run `scripts/repair_vault.py --vault ${VAULT_PATH} --project ${PROJECT_TAG}` and report what it fixed. No harvest, no distill, no consolidation. This is the **only** mode besides a real run that modifies vault files — and it only ever rewrites specific frontmatter fields, adds missing reverse wikilinks, and backticks render-breaking tokens. It never deletes content.

Why this exists: template/spec fixes only apply to newly-generated files. A vault made by an older skill version stays broken forever unless a repair pass reconciles it. `/synthmem repair` is what makes the v0.6.3 validator + gate *useful* rather than just *accusatory*.

Deterministic fixes: meta/archive/log tag normalization to the canonical 5-distinct tuple; `slug` set to filename-stem-minus-prefix; missing reverse wikilinks added; archive content-type → `summary`; bare `<…>` tokens backticked. Genuine duplicate-domain-tag cases on `node_`/`entity_` files are **flagged, not auto-fixed** (they need a semantic re-tag).

After repair, run the validator and show the before/after verdict. Recommend `/synthmem repair` whenever the validation gate reports pre-existing (out-of-scope) errors.

### `/synthmem --dry-run` — preview, write nothing

If invoked with `--dry-run`, produce a **plan** of what a real run would do, then exit having written **nothing**.

Allowed (all read-only): resolve config, compute the time window, harvest sessions (`find_sessions.py` + `parse_session.py`), and a **planning pass** of the distiller — decide which `node_*`/`entity_*` it would create / update / merge, the slug + 5 tags it would assign, the wikilinks it would add, which files compaction would archive, any bucket it would auto-create. Do **not** generate full node bodies (metadata-level plan only — keeps it cheap).

**Hard prohibition in dry-run** (this is a guardrail, not a preference): no `Write`/`Edit` anywhere under `${VAULT_PATH}`, no `mkdir` of subdirectories, no `update_state.py`, no compaction moves. If any step would write, it instead records the intent into the plan.

Output a single structured report **to the chat** (never to a file):

```
DRY RUN — no changes written. Vault: ${VAULT_PATH}

Window: <from> → <now>   (<N> sessions across <D> days)
Tooling: scripts_ok | fallback

Would create:  <X> nodes, <Y> entities, <Z> chats, <W> logs
Would update:  <list of existing slugs + why>
Would merge:   <a → b (reason)>
Would link:    ~<E> new wikilink edges
Would archive: <files compaction would move>
Would create buckets: <name/ (reason) | none>
Validation prediction: <PASS | REVIEW | FAIL with expected issues>

Run `/synthmem` (no --dry-run) to apply.
```

`--dry-run` may combine with `--since`/window flags. It is the safe way to answer "what happens if I run this after 3 weeks away?" without committing.

The user expects to leave this running and come back later. **Do not ask clarifying questions mid-run unless something is genuinely blocking** (missing config, unreadable session directory, vault path doesn't exist). The **first-run** prompt is the single documented exception.

## Tooling detection (do this FIRST in every run)

Helper scripts in `${SKILL_DIR}/scripts/` accelerate session parsing and state updates. Detect availability at the start of every run:

```bash
command -v python3 >/dev/null 2>&1 \
  && [ -f "${SKILL_DIR}/scripts/find_sessions.py" ] \
  && echo "scripts_ok" \
  || echo "fallback"
```

- **`scripts_ok`** → call `find_sessions.py`, `parse_session.py`, `update_state.py` via `Bash` for all mechanical work (JSONL parsing, state mutations). Fast, deterministic.
- **`fallback`** → parse inline using the rules in `references/session-source.md`, and update `_state.json` by Read + Edit (with extra care for atomicity). Slower and more token-expensive, but functional.

If a script invocation fails (non-zero exit), fall back inline for that operation and continue. Note tooling mode in the run report.

See `scripts/README.md` for the full contract and exit-code conventions.

## Multi-agent orchestration (default)

Dispatch sub-agents in parallel using the `Agent` tool. The pipeline:

```
harvester → distiller → linker → indexer
```

See `references/multi-agent-orchestration.md` for each sub-agent's contract, including the long-session chunking rule (sessions with > 100 turns must be processed in 50-turn chunks by the distiller).

For tiny runs (one short session, init-only) you may do this inline without spawning sub-agents. The orchestrator decides per run.

## Vault structure — typed subdirectories, lazy creation

Read `references/vault-structure.md` for the full spec. Quick reference:

- **Root** (4 meta files only): `_INDEX.md`, `_RECENT.md`, `_state.json`, `README.md`.
- **`nodes/`**: one `node_*.md` per consolidated concept. Created on first node write.
- **`entities/`**: one `entity_*.md` per named thing. Created on first entity write.
- **`chats/`**: one `chat_*.md` per Claude Code session. Created on first chat write.
- **`logs/`**: one `log_*.md` per run day. Created on first log write.
- **`archives/`**: rollups (`_archive_YYYY-WW.md`, `_archive_YYYY-MM.md`). Created on first compaction.

All subdirectories are created **lazily** — never preemptively. A fresh vault has only the 4 meta files.

**Migrating from v0.5/v0.6.0**: if the vault has `node_*.md` or `entity_*.md` at the root, the indexer moves them into `nodes/` and `entities/` on the first v0.6.1 run and records this in `_state.json` (`migrated_to_typed_subdirs: true`). Wikilinks survive (basenames).

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
9. **Never create speculative subdirectories.** Only the standard ones (`nodes/`, `entities/`, `chats/`, `logs/`, `archives/`), and only when actually writing into them. Additional buckets are created **autonomously** but only when the YAGNI threshold (≥ 20 files of a distinct prefix at the root) is crossed — see `references/vault-structure.md`. New buckets must always be reported in `logs/log_YYYYMMDD.md`.
10. **Never emit raw Markdown-breaking characters in generated content.** Any literal `<` / `>` (paths, placeholders, generics like `<proj>`, env vars, shell snippets) MUST be wrapped in backticks (`` `~/.claude/projects/<proj>/` ``) or escaped (`&lt;` / `&gt;`). Obsidian and most renderers parse a bare `<word>` as an unclosed HTML tag and silently destroy everything after it — including subsequent headings and list items. This applies to `_INDEX.md`, `_RECENT.md`, node/entity bodies, log reports — *every* generated file. See `references/frontmatter-spec.md` → "Markdown-safe output".
11. **Never create `status: draft` stub files for one-off dangling wikilinks.** Leave them unresolved (Obsidian "create new" anchors). Only materialize a draft stub when a dangling target is referenced by ≥ 3 distinct files. See `references/vault-structure.md`.
12. **The linker must produce node↔node links, not just chat↔node.** An isolated `node_*` (`linked_nodes: []`) after a run is a linker failure. See `references/multi-agent-orchestration.md` → linker phase 2.
13. **In `--dry-run`, write absolutely nothing.** No `Write`/`Edit` under `${VAULT_PATH}`, no subdirectory `mkdir`, no `update_state.py`, no compaction moves. A dry run that mutates the vault is a critical bug. Every would-be write becomes a line in the plan report instead.
14. **If anything is ambiguous or risky, stop and report**, do not guess.

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
- Tooling: scripts_ok | fallback
- First-run mode: ask | today | full | 7d | ... (only present on first run)
- Sessions processed: <N>
- Date range: YYYY-MM-DD → YYYY-MM-DD
- New nodes: <list of slugs>
- New entities: <list of slugs>
- Updated nodes: <list of slugs, with merge notes if same-root merges happened>
- Merges performed: <e.g. "node_synthmem-helper-scripts → node_synthmem (same-root merge)">
- Concepts NOT promoted (kept inline in chats): <count + 1-line reason>
- Archived: <count of files moved to archives/>
- Subdirectories created this run: <list, if any — e.g. "nodes/, entities/ (first content)">
- Buckets auto-created: <e.g. "decisions/ (23 decision-* files moved in)">
- Vault migrated to typed subdirs: <true on the v0.6.1 upgrade run, omitted otherwise>
- Warnings: <anything the user should know>
- Errors / retries needed: <session ids, if any>
```

Then tell the user, briefly, what was done. They may be asleep; keep it tight.
