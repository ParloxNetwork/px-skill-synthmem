# Changelog

All notable changes to this skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is semantic in spirit: `MAJOR.MINOR.PATCH`.

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
