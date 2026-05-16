# Changelog

All notable changes to this skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is semantic in spirit: `MAJOR.MINOR.PATCH`.

## [0.6.10] — tag-taxonomy linter (closes v0.6 Hardening)

### Added
- **`validate_vault.py` `tag-genericity` check**: flags an umbrella/placeholder term (curated denylist, kept in sync with `tag-taxonomy.md` "Genericity lint") used in a domain slot (positions 1–3). **Advisory only** — a warning, never an error; never blocks the gate; never auto-repaired (a tag's meaning needs semantic judgement, not a mechanical rewrite). Surfaced in the day-log `## Para revisar (opcional)`. `unfiled` exempt on `status: draft` files (intentional stub placeholder). 0 false positives on the real vault (the distiller's tag discipline is solid).

### Tried and reverted (honest engineering)
- **Vocabulary-drift heuristic** (flag a tag that is the token-prefix of ≥3 other tags): prototyped, dropped. False-positived on legitimate hierarchical tags — `claude-code` is a *good* specific tag but looks like an umbrella of `claude-code-skills`/`claude-code-memory`. A stdlib script can't tell a parent from a too-generic tag without semantics; a noisy advisory is worse than a precise one. Denylist is the only signal.
- **Archive↔chat watch-item fix**: honoring `_archive_*` body wikilinks in the symmetrizer regressed asymmetric-link count **0 → 88** (an archive body is a consolidation dump referencing dozens of files; forcing bidirectionality bloats `linked_nodes`). Reverted. The ~2 residual archive↔chat warnings are cosmetic and non-blocking; shipping a regression to close them is worse. Documented as a known minor limitation in ROADMAP.

### Milestone
**v0.6 (Hardening) is COMPLETE** — v0.6.0 → v0.6.10. The skill is autonomous end-to-end (process → validate → auto-heal → finalize) with status/retry/dry-run/repair tooling and an advisory tag linter. Next: v0.7 (multi-IA) or public promotion from v0.6.x.

## [0.6.9] — `/synthmem --retry`

### Added
- **`/synthmem --retry`**: reprocess **only** the sessions in `pending_sessions` (not the catch-up window). Same harvest→distill→link→index→gate, scoped to failures. Empty queue → "nothing to retry", exit 0.
- **`update_state.py --action bump-retry`** + `pending_attempts` map + `MAX_RETRY_ATTEMPTS=3`. A session that fails 3 times is auto-removed from `pending_sessions` and recorded in `dropped_sessions` (surfaced to the user) — a permanently-broken session can never cause an infinite retry loop, preserving the autonomy contract. `remove-pending` now also clears the session's attempt counter.
- `catch-up-logic.md` Step 3a pins the retry-counter mechanism; normal runs still auto-resume pending work, `--retry` is the explicit scoped form.

## [0.6.8] — `/synthmem status`

### Added
- **`skill/scripts/status_vault.py`** + **`/synthmem status`**: read-only operational dashboard. Reports vault size + per-subdir file counts, last-run timestamp/status, total sessions processed + streak, draft-stub count, pending sessions (with a `/synthmem --retry` hint), and days elapsed since the last run. Reads `_state.json` + filesystem only — no validation, no writes, fast on large vaults. Clear separation: `status` = operational snapshot, `validate` = correctness, `repair` = fix.
- Measured on the real vault: 538.8 KB / 138 files, last run [completed], 0 pending, 7 draft stubs — instant.

## [0.6.7] — linker root-cause fix (caught by v0.6.6 observability)

v0.6.6's observability split did exactly its job on the first autonomous run: it flagged that the LLM linker emits ~176 asymmetric links **every run** (auto-heal was silently cleaning 73 files each time) and that 16 frequently-referenced `node_` concepts were dangling graph gaps. v0.6.7 fixes both at the root instead of patching symptoms each run.

### Added / Changed
- **`repair_vault.py --links-only`** + **linker phase 3** (mandatory deterministic final step): the LLM linker does the *semantic* forward-linking (phases 1–2); a script then does the *mechanical* graph integrity — symmetrize every `A→B` into `B→A`, and materialize `status: draft` stubs for any target referenced by ≥3 files. Bidirectionality and ≥3-ref safety nets are bookkeeping, not judgment → scripted (v0.6.0 principle). The validation gate now sees zero asymmetric links: **no per-run auto-heal churn**.
- **Fix B**: ≥3-ref stub materialization now covers **`node_` as well as `entity_`** (v0.6.6 only stubbed entities, leaving 16 frequently-referenced node concepts dangling). The distiller fleshes these out the next time the concept appears in a session.
- Guardrails #11/#12 and the Link workflow step rewritten to point at the deterministic phase 3.

### Measured
On the post-v0.6.6 real test vault: `repair_vault.py --links-only` took it from REVIEW (0 errors / 16 warnings — the 16 dangling ≥3-ref nodes) to **PASS (0 errors / 0 warnings)**, creating the exact 16 node-stubs the validator had flagged (`brand-axis-positioning` 6 refs, `wordpress-to-hugo-migration` 5, …) and symmetrizing the rest.

### Notes
This is the pattern again: autonomous run → observability signal → root-cause fix. The signal we built into v0.6.6 paid for itself immediately. v0.6.8 next: `/synthmem status`.

## [0.6.6] — auto-heal (autonomy-first)

User-driven: the core principle is "type `/synthmem` at end of day, leave the machine on, come back to a finished vault — no subcommands." v0.6.5 made the vault *fixable* but still required the user to type `/synthmem repair`. v0.6.6 makes it automatic. Roadmap reordered: auto-heal promoted ahead of `status`.

### Added
- **Validator-triggered auto-repair** inside every `/synthmem` run. If the scope-aware validator finds any deterministically-fixable drift (tag distinctness, slug≠filename-tail, asymmetric wikilinks, archive content-type, markdown `<…>`) — legacy *or* introduced this run — `repair_vault.py` runs automatically, then the validator re-runs. Skipped entirely when the vault is already clean (zero cost on healthy runs).
- **Observability split**: repair's fixes are logged as **legacy** (expected, count only) vs **in-scope** (`⚠ distiller-smell: investigate`) so silent self-healing never masks a distiller/linker bug.
- **Autonomy contract** (SKILL.md): the run always reaches a terminal state (finalized, or `partial` with a logged reason); it never hangs for input; sub-agent failures mark-pending-and-continue; anything needing human judgment is surfaced (one line in the final summary + `## Para revisar (opcional)` in the day's log), never blocking.

### Changed
- Pipeline steps 8–12 restructured: validate → auto-heal loop → finalize → report. Non-auto-fixable `flagged` items finalize anyway (blocking would create a stuck overnight state — anti-autonomy).
- `/synthmem repair` remains as a manual/debug standalone but is **no longer required** for routine operation.
- ROADMAP reordered: v0.6.7 `status`, v0.6.8 `--retry`, v0.6.9 tag linter.

### Notes
This is the feature that fulfills the original promise: end your day, run `/synthmem`, sleep, return to consolidated + reconciled + validated — hands-off. No new script (auto-heal orchestrates the existing v0.6.3 validator + v0.6.5 repair). v0.6.7 next: `/synthmem status`.

## [0.6.5] — repair pass + scope-aware validation gate

The v0.6.4 dry-run surfaced an architectural gap: template/spec fixes only apply to newly-generated files, so a vault made by an older skill version stays broken forever, and the v0.6.3 gate would keep `_state.json` at "partial" indefinitely on legacy errors. v0.6.5 closes that gap. Roadmap reordered: `repair` promoted ahead of `status`.

### Added
- **`skill/scripts/repair_vault.py`** + **`/synthmem repair`**: deterministic reconcile of an existing vault. Fixes: meta/archive/log tag normalization to the canonical 5-distinct tuple; `slug` → filename-stem-minus-prefix; missing reverse wikilinks added; archive content-type → `summary`; bare `<…>` tokens backticked. **Never deletes content** — only rewrites targeted frontmatter fields / `linked_nodes` / backticks bodies, and bumps `last_updated`. Genuine duplicate-domain-tags on `node_`/`entity_` are flagged (not auto-fixed — need a semantic re-tag).
  - Measured on the v0.6.2 test vault: **FAIL (6 errors / 130 warnings) → REVIEW (0 errors / 2 warnings)**, 72 files fixed, 0 flagged. Body content preserved byte-for-byte (verified line counts).
- **Scope-aware gate**: `validate_vault.py --changed "<files this run touched>"`. ERRORs in touched files still block; ERRORs in untouched legacy files are demoted to warnings tagged "pre-existing (run /synthmem repair)". A clean run is no longer blocked forever by old issues; the gate points at `repair` instead of stalling.

### Changed
- Pipeline gate (SKILL.md step 8, multi-agent-orchestration.md): now scope-aware; finalizes on out-of-scope-only errors while telling the user to run `/synthmem repair`.
- ROADMAP reordered: v0.6.6 `status`, v0.6.7 `--retry`, v0.6.8 tag linter.

### Resolved
- Watch-item "asymmetric wikilinks (~79)": `repair` adds the missing reverse links. 2 residual archive↔chat edges remain (archive body refs) — logged as a minor watch-item.

### Notes
`repair` is the piece that makes the validator+gate *useful* rather than merely *accusatory*, and it's a prerequisite for public promotion (early adopters' vaults must be fixable). v0.6.6 next: `/synthmem status`.

## [0.6.4] — `--dry-run` preview mode

### Added
- **`/synthmem --dry-run`**: full read-only preview. Resolves config, computes the catch-up window, harvests sessions, and runs a metadata-level planning pass (which nodes/entities it would create/update/merge, slug + 5 tags, wikilink edges, compaction moves, bucket creation). Prints one structured plan to the chat and exits having written **nothing** — no files, no lazy subdirs, no `_state.json`. Combines with `--since`/window flags.
- Hard guardrail #13: a dry run that mutates the vault is a critical bug; every would-be write becomes a plan line instead.
- Sub-agent dry-run contracts documented (harvester runs normally as it is already read-only; distiller plans-only; linker computes edge counts; indexer computes-but-does-not-write; validation gate runs against the unchanged vault as a baseline + predicts the post-run verdict).

### Notes
No script needed — dry-run is a behavior, not a tool (YAGNI). The cheap, safe answer to "what would happen if I run this after 3 weeks away?". v0.6.5 next: `/synthmem status`.

## [0.6.3] — Validator (and the bugs it immediately caught)

Added the deterministic vault validator from the hardening backlog. It earned its keep on first run by proving v0.6.2.1's distinctness fix was incomplete and surfacing a latent slug-convention inconsistency.

### Added
- `skill/scripts/validate_vault.py` — read-only, Python stdlib. Checks frontmatter completeness, `type`↔subdir placement, slug==filename-tail, 5 distinct tags, content-type vocabulary, ISO dates, broken/asymmetric/isolated wikilinks, dangling targets that should be stubs (≥3 refs), near-duplicate slugs/titles, raw `<…>`/pipe/leading-`#` markdown hazards, binaries, root cleanliness. Exit 5 on ERROR-level issues.
- **Validation gate** in the pipeline: the indexer runs the validator before finalizing; `_state.json` is finalized only if zero ERROR-level issues, else `last_run_status: "partial"`.
- **`/synthmem validate`** — read-only audit subcommand. Runs the validator against the existing vault, no consolidation, no writes. Cheap scale-testing.

### Fixed (caught by the new validator)
- **Meta templates still violated distinctness.** v0.6.2.1 only fixed `log.md`; `_INDEX.md` (`[meta, index, navigation, meta, vault]`), `_RECENT.md`, and `_archive.md` still had duplicate tags. Rewritten to 5 distinct tags each.
- **Archive content-type.** Archives used `archive` in position 4 (not in the fixed vocabulary). Now `summary` (archives are period summaries).
- **Chat slug convention inconsistency.** Chat slug was `YYYYMMDD-<id>` (hyphen) while the filename tail is `YYYYMMDD_<id>` (underscore) — 50 false-positive-looking warnings that were actually a real inconsistency. Canonical rule now documented and enforced: **slug == filename stem minus the type prefix, verbatim**. Time-keyed types (chat/log/archive) are exempt from kebab-only; semantic types (node/entity) keep kebab-case. `chat.md` template fixed; `vault-structure.md` "Slug rules" rewritten.

### Notes
The validator replaces ad-hoc LLM sanity-checking with a reproducible gate (v0.6.0 principle: mechanical work is scripted, not eyeballed). Vault-content warnings from the pre-v0.6.3 test vault (asymmetric links, etc.) clear naturally on the next `/synthmem` run with current templates. v0.6.4 next: `--dry-run`.

## [0.6.2.1] — Third-run polish

The third real run validated v0.6.2 (0/32 isolated nodes, clean tags, church-context memory applied, no markdown breakage). Two small misses remained.

### Fixed
- **Distinctness invariant now covers logs.** v0.6.2 enforced unique tags for nodes/entities but the log path still carried the old pattern: `templates/log.md` and the `tag-taxonomy.md` log example repeated the project tag in a domain slot, and a stale note said "repeat is expected" for logs. The generated `log_*.md` ended up with `synthmem-dev` in positions 2 and 5. Log tags now follow the same 5-distinct rule (`daily-log`, run-domain, `vault-ops`, `summary`, project).
- **Removed `last_skill_version`.** Introduced in v0.6.1 as "informational", it was a hardcoded constant in `update_state.py` that lagged the real release (showed `0.6.1` while v0.6.2 ran). Per the project's versioning philosophy (git history is the single source of truth; a stale string is worse than none), the vault now carries **no version field at all**. Removed from `update_state.py`, `_state.json` template, and `catch-up-logic.md`.

### Notes
Pure corrections, no features. v0.6.3 resumes the hardening backlog (validator).

## [0.6.2] — Corrections from second real run (graph + tags + render safety)

The first full month-scale run worked structurally (clean root, typed subdirs, quality bar held) but surfaced six issues — four spec/behavior gaps and two reported by the user. No new features.

### Fixed
- **Linker now builds an actual graph (critical).** v0.6.1 produced 51/53 nodes with `linked_nodes: []` — nodes connected only through chat hubs (star topology, not a knowledge graph). The linker spec now has an explicit **phase 2: semantic node↔node linking** (explicit mention, shared-domain affinity, parent/child), bounded to ≤7 links/node, with an acceptance check (>30% isolated nodes = linker failure, must re-scan).
- **Tag assignment order (5 → 4 → 3) with distinctness invariant.** v0.6.1 picked domain tags first and frequently echoed one in the project/content-type slot (`[teologia-sistematica, …, reference, teologia]`; `synthmem-dev` in positions 1 and 5). Now: project context resolved first (a real project, never a topic), content-type second, then 3 domain tags that must not collide with positions 4–5. All 5 tags must be unique.
- **Conservative merge rule.** The v0.6.0/0.6.1 "merge if slugs share the token before the first `-`" rule would have collapsed 9 distinct `claude-code-*` nodes into one. Rewritten: merge only on slug-containment/near-identical-title **and** content overlap; otherwise keep separate and link.
- **Dangling wikilinks left unresolved (spec aligned to behavior).** Spec previously said "create a `status: draft` stub" for every dangling link; real behavior (leaving them as Obsidian "create new" anchors) is better. Spec now matches: stubs only when a target is referenced by ≥ 3 distinct files.
- **Markdown-safe output (user-reported).** A bare `<proj>` in a path inside `_INDEX.md` was parsed by Obsidian as an unclosed HTML tag, destroying rendering of everything below it (headings included). New hard guardrail + `frontmatter-spec.md` → "Markdown-safe output": backtick or escape `<`, `>`, stray `|`, leading `#` in all generated files; final pass before every write.

### Changed
- `SKILL.md` hard guardrails extended (markdown safety, dangling-link policy, linker-must-graph) and renumbered.
- `tag-taxonomy.md`, `frontmatter-spec.md`, `multi-agent-orchestration.md` rewritten in the affected sections.

### Notes
v0.6.2 closes the second corrections cycle. Vault structure and human-readability (the user explicitly browses it in Obsidian) are now the priority bar alongside "frontmatter parses". v0.6.3+ resume the hardening backlog (validator, dry-run, status, retry, tag linter).

## [0.6.1] — Corrections from first real run

After the first end-to-end `/synthmem` run, five issues surfaced that this release fixes. No new features.

### Fixed
- **Config path resolution**: the skill now reads `_local/config.json` from the skill's installed directory (`readlink -f ~/.claude/skills/synthmem` → repo root), with XDG fallback for copy installs. Previously the skill looked relative to the cwd, silently creating a new config with inferred defaults when run from inside the vault.
- **Root oversaturation**: `node_*` and `entity_*` files now live in `nodes/` and `entities/` subdirectories (lazy creation). The vault root holds only meta files (README, _INDEX, _RECENT, _state.json). Pre-v0.6.1 vaults auto-migrate on first run via the indexer.
- **Distiller over-fragmentation**: added a strict quality bar — a concept is promoted to a standalone `node_*` only if it appears in ≥ 2 sessions, has ≥ 200 distillable words, or is explicitly marked by the user. Same-root slugs (e.g., `synthmem-helper-scripts` vs `synthmem-skill`) now merge by default.
- **First-run prompt suppression**: in v0.6.0 the prompt was silently skipped when the runtime suggested autonomous mode. v0.6.1 adds `first_run_default: ask | today | full | <N>d` to the config. Default is `ask`. Non-interactive runtimes fall back to `today` and record the fallback.

### Changed
- `_state.json` no longer carries `vault_version` (it conflated skill version with vault). Added `last_skill_version` (informational) and `migrated_to_typed_subdirs` (one-time flag). The vault's own history is git's job, not the state file's.
- `schema.vault_layout` bumped to `"2.0"` to reflect the typed-subdirectory layout.
- Bucket detection regex updated for the new root (only `README` and `_*` should appear at the root).
- Templates (`README.md`, `_state.json`, `_INDEX.md`) updated for the new layout.

### Notes
v0.6.1 closes the corrections cycle from real-world testing. v0.6.2+ resume the hardening backlog (validator, dry-run, status, retry, tag linter).

## [Unreleased] — v0.6 hardening (in progress)

### Added
- `skill/scripts/` — Python stdlib helpers (`find_sessions.py`, `parse_session.py`, `update_state.py`) for fast, deterministic JSONL parsing and atomic `_state.json` updates.
- Tooling detection at run start: skill uses scripts when Python 3.8+ is on PATH; falls back to inline AI parsing otherwise. Mode is reported in the daily log.
- Long-session chunking rule: distiller sub-agent processes sessions with >100 turns in 50-turn chunks, producing one consolidated `chat_*.md` regardless.
- Autonomous bucket creation: when a non-standard filename prefix accumulates ≥20 files at the vault root, the indexer creates `<prefix>s/`, moves the files in, and reports the action in the daily log. Max one new bucket per run. User can override by `mv`ing files back.

### Changed
- `_state.json` schema bumped to `vault_version: "0.6.0"` (managed by `update_state.py`).
- `INSTALL.md`: documents Python 3.8+ as an optional accelerator (not a requirement).

### Notes
v0.6 in progress — accelerator scripts + chunking + autonomous bucket creation landed. Remaining items: validator, `--dry-run`, `status`, `--retry`, tag linter.

## [0.5.0] — Initial public scaffold

### Added
- Skill structure: `skill/SKILL.md`, 8 reference docs, 9 templates.
- `/synthmem` slash command with `init`, `status`, `--since`, `--dry-run`.
- Hybrid vault layout: semantic core at root (`node_*`, `entity_*`); high-cardinality types in lazy subdirectories (`chats/`, `logs/`, `archives/`).
- Lazy directory creation — subdirectories appear only when first file is written.
- YAGNI rule for custom subdirectories: new buckets only when ≥ 20 same-type files accumulate.
- Multi-agent orchestration as the default (harvester → distiller → linker → indexer; optional reviewer).
- 5-tag taxonomy (3 domain + 1 content-type + 1 project).
- Bidirectional wikilink contract using basenames (portable across subdirs).
- Non-destructive compaction: weekly + monthly archives, originals preserved.
- First-run interactive bootstrap: today / full history / custom window.
- Day-by-day state checkpointing in `_state.json` (interrupt-safe).
- `_local/` configuration scaffolding (fully gitignored; public template at repo root as `config.example.json`).
- README, INSTALL, ROADMAP.
- AGPL-3.0-or-later license (LICENSE).

### Notes
First public release. Expect refinements in v0.6 once the design sees real-world use. Encryption-at-rest is intentionally deferred to "Future" (no committed version) per current scope.
