# Roadmap

Synthmem is built incrementally. v0.5 is the first public-shaped scaffold; later versions add polish, breadth, and protection. v1.0 is reserved for the first version we'd recommend without caveats.

## v0.5 — Scaffold (current)

- [x] Hybrid Markdown vault: semantic core at root (`node_*`, `entity_*`), high-cardinality types in lazy subdirectories (`chats/`, `logs/`, `archives/`).
- [x] YAML frontmatter with 5-tag schema (3 domain + 1 content-type + 1 project).
- [x] Bidirectional wikilinks (`[[node_x]]`) using basenames for portability across subdirs.
- [x] `/synthmem` user-triggered consolidation command.
- [x] Catch-up: detect last run and process the gap, day-by-day with state checkpointing.
- [x] First-run UX: interactive bootstrap choice (today / full history / custom window).
- [x] Multi-agent orchestration (harvester → distiller → linker → indexer).
- [x] Non-destructive compaction: weekly snapshots, monthly archives, originals preserved.
- [x] `_local/` for user-specific config (gitignored); public template at the repo root.
- [x] Generic skill — zero personal data in the public repo.
- [x] AGPL-3.0-or-later license.
- [x] YAGNI directory rule: new subdirectories only when ≥ 20 same-type files accumulate.

## v0.6 — Hardening

- [ ] Validator script: lints frontmatter, detects broken wikilinks, flags duplicate concepts.
- [ ] `--dry-run` mode: preview what `/synthmem` would do, without writing.
- [ ] `/synthmem status`: report vault size, last-run, pending sessions, errors.
- [ ] `/synthmem --retry`: reprocess failed sessions explicitly.
- [ ] Tag-taxonomy linter: warn if a tag is "too generic" relative to existing nodes.

## v0.7 — Multi-IA support

- [ ] Adapter pattern for session sources (Claude Code, Codex CLI, Gemini CLI, others).
- [ ] Document the adapter interface so the community can contribute.
- [ ] Cross-IA chat-merge: same day, multiple tools → one consolidated log.

## v0.8 — MCP server

- [ ] Expose the vault as an **MCP server** so any MCP-compatible client (Claude Desktop, Claude Code, others) can query it on demand: "what did I decide about X last month?"
- [ ] Read-only by default; write only via `/synthmem`.

## v0.9 — UX polish

- [ ] Obsidian-specific helpers: `.obsidian/graph.json` template that highlights node-type by color.
- [ ] Optional summary email at end of consolidation (top concepts, new entities, archived count).
- [ ] Search helpers documented for non-Obsidian users (`grep`, `rg`, `fzf` recipes).

## v1.0 — Production-ready (promotable)

- [ ] Selective sync: ignore-list / include-list rules per project.
- [ ] Conflict resolution if two machines run `/synthmem` against the same vault.
- [ ] Stable contracts: frontmatter schema, sub-agent interfaces, vault layout — no breaking changes after this point without a `v2.0`.

## Future (no committed version)

- [ ] Vault encryption at rest (age / sops) for repos that need it. Deferred until there is a concrete user need.
- [ ] GitHub Actions / push automation for the public repo (separate concern from the vault).

## Out of scope (intentional)

- ❌ Embedding/vector indexing. Plain text + grep + Claude's reading ability is enough.
- ❌ Live session hooks. The skill is **batch-by-design**.
- ❌ Storing binaries (images, audio, PDFs). Only references to them.
- ❌ Web UI. The vault is the UI; Obsidian + your editor are the viewers.
