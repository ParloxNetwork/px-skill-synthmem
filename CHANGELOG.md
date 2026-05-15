# Changelog

All notable changes to this skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is semantic in spirit: `MAJOR.MINOR.PATCH`.

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
