# Changelog

All notable changes to this skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is semantic in spirit: `MAJOR.MINOR.PATCH`.

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
