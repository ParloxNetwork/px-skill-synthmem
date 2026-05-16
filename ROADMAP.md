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

## v0.6 — Hardening (in progress)

Each item lands as its own patch release (v0.6.x).

### v0.6.0 — foundation
- [x] Helper scripts in `skill/scripts/` (Python stdlib; graceful fallback if missing).
  - `find_sessions.py` — list sessions overlapping a date range.
  - `parse_session.py` — structured turns from one JSONL.
  - `update_state.py` — atomic mutations on `_state.json` with file locking.
- [x] Long-session chunking: distiller processes sessions >100 turns in 50-turn chunks.
- [x] Autonomous bucket creation: ≥20-file prefix patterns trigger bucket creation + reporting (no user intervention required).

### v0.6.1 — corrections from first real run
- [x] Config path bug: resolve `_local/config.json` from the skill's installed dir (not cwd). Adds XDG fallback for copy installs.
- [x] Typed subdirectories: `nodes/` and `entities/` (lazy) — root holds only meta files. Migrates pre-v0.6.1 vaults automatically.
- [x] Distiller quality bar: promotion threshold (≥2 sources OR ≥200 words OR explicit user marker); aggressive same-root merging to fight fragmentation.
- [x] `first_run_default` config flag: `ask | today | full | <N>d`. Default `ask`. Fallback to `today` in non-interactive runtimes.
- [x] Removed `vault_version` from `_state.json`; added `last_skill_version` (informational). Git history is the vault's own changelog.

### v0.6.2 — corrections from second real run (graph + tags + render safety)
- [x] Linker phase 2: semantic node↔node linking (was star topology; 51/53 nodes were isolated).
- [x] Tag assignment order 5→4→3 with distinctness invariant (project never echoes a domain).
- [x] Conservative merge rule (no more "same leading token" over-merging).
- [x] Dangling wikilinks left unresolved; draft stub only at ≥3 references (spec aligned to behavior).
- [x] Markdown-safe output: backtick/escape `<` `>` `|` leading-`#` in all generated files (Obsidian render fix).

### v0.6.2.1 — third-run polish
- [x] Distinctness invariant now applied to **logs** too: `templates/log.md` and the `tag-taxonomy.md` log example no longer repeat the project tag in a domain slot. Removed the contradicting "repeat is expected" note.
- [x] Removed `last_skill_version` entirely (a hardcoded string that lagged the actual release — 0.6.1 vs 0.6.2). The vault now carries **no version field at all**; git tags/commits are the single source of truth. Supersedes the v0.6.1 line above.

### v0.6.3 — validator
- [x] `validate_vault.py`: deterministic read-only health check (frontmatter, slug==filename-tail, 5 distinct tags, content-type vocab, broken/asymmetric/isolated wikilinks, near-dup slugs/titles, markdown hazards, binaries). Exit 5 on errors.
- [x] Validation gate: indexer runs it pre-finalize; `_state.json` finalized only if zero errors.
- [x] `/synthmem validate` read-only subcommand (audit a big vault with no reprocess).
- [x] Fixed bugs the validator caught: meta templates (`_INDEX`/`_RECENT`/`_archive`) had duplicate tags; archive content-type → `summary`; canonical slug rule (slug == filename-tail) documented + chat template fixed.

### v0.6.4 — `--dry-run`
- [x] `/synthmem --dry-run`: full read-only preview (config + window + harvest + metadata-level plan), prints a plan, writes nothing (no files, no subdirs, no `_state.json`). Guardrail #13. Sub-agent dry-run contracts documented.

### v0.6.5 — repair pass + scope-aware gate
- [x] `repair_vault.py` + `/synthmem repair`: deterministic reconcile of legacy vaults — meta/archive/log tag normalization, slug==filename-tail, missing reverse wikilinks, archive content-type, markdown backticking. Never deletes content. Genuine node/entity dup-tags flagged (not auto-fixed). On the v0.6.2 test vault: FAIL (6 err/130 warn) → REVIEW (0 err/2 warn).
- [x] Scope-aware gate: `validate_vault.py --changed <files>` demotes out-of-scope (legacy) errors to warnings tagged "pre-existing (run /synthmem repair)" so a clean run is never blocked forever by old issues. Resolves the v0.6.4 dry-run finding.
- [x] Resolves the asymmetric-wikilinks watch-item: `repair` adds the missing reverse links (the ~79 case → 2 residual archive↔chat edges).

### v0.6.6 — auto-heal (autonomy-first)
- [x] Validator-triggered auto-repair inside every `/synthmem` run: if validation finds deterministically-fixable drift (legacy or in-scope), `repair_vault.py` runs automatically, then re-validates. Zero cost when the vault is already clean. The user never needs to type `/synthmem repair` for routine operation (it stays as a manual/debug subcommand).
- [x] Observability split preserved: in-scope fixes logged as `⚠ distiller-smell: investigate` so silent self-healing doesn't mask distiller bugs.
- [x] Non-auto-fixable `flagged` items never block: surfaced in the day's log `## Para revisar (opcional)` + one concrete line in the final user summary. The run always reaches a terminal state.
- [x] Autonomy contract documented in SKILL.md: type `/synthmem`, leave overnight, return to a finished vault — no subcommands, no hangs, errors self-identified and the flow always completes.

### v0.6.7 — linker root-cause fix (caught by v0.6.6 observability)
- [x] **Fix A — deterministic link symmetry**: `repair_vault.py --links-only` (linker phase 3). The LLM linker does semantic forward-linking; a mandatory deterministic final step symmetrizes every `A→B` into `B→A`. v0.6.6's `⚠ distiller-smell` exposed ~176 asymmetric links/run that auto-heal was cleaning across 73 files *every run*. Now the gate sees zero — no per-run churn. Bidirectionality is bookkeeping → script, not LLM (v0.6.0 principle).
- [x] **Fix B — ≥3-ref node stubs**: the ≥3-referrer stub rule now materializes `node_` stubs too, not only `entity_`. The 16 frequently-referenced concepts (3–6 refs each) that were dangling graph gaps now become `status: draft` stubs the distiller fleshes out later. Measured: post-v0.6.6 test vault REVIEW (16 warnings) → **PASS (0)**.

### v0.6.8 — `/synthmem status`
- [x] `status_vault.py` + `/synthmem status`: read-only operational dashboard (vault size, file counts, last-run, streak, draft stubs, pending sessions, days since last run). No validation, no writes; fast on large vaults. Clear separation status / validate / repair.

### v0.6.9 — `/synthmem --retry`
- [x] `/synthmem --retry` reprocesses only `pending_sessions`. `update_state.py --action bump-retry` + `pending_attempts` + `MAX_RETRY_ATTEMPTS=3` → a broken session auto-drops into `dropped_sessions` (surfaced), never loops forever. Normal runs still auto-resume; `--retry` is the explicit scoped form.

### v0.6.10 — tag-taxonomy linter (closes v0.6 Hardening) ✅
- [x] `validate_vault.py` `tag-genericity` check: an umbrella/placeholder term (curated denylist, synced with `tag-taxonomy.md`) used in a domain slot is flagged. **Advisory only** — warning, never error; never blocks the gate; never auto-repaired (a tag's meaning needs semantic judgement). `unfiled` exempt on `status: draft`. 0 false positives on the real vault.
- [x] Vocabulary-drift heuristic **prototyped and dropped**: it false-positived on legitimate hierarchical tags (`claude-code` flagged because `claude-code-skills` exists). A stdlib script can't distinguish a parent tag from a too-generic one; the precise denylist is the only signal.
- [~] **Archive↔chat watch-item: attempted, reverted.** Honoring `_archive_*` body wikilinks in the symmetrizer regressed asymmetric-link count 0 → 88 (an archive body is a consolidation dump referencing dozens of files; forcing bidirectionality on all bloats `linked_nodes`). The ~2 residual archive↔chat warnings are cosmetic and non-blocking; shipping that regression to close them is worse. **Left as a documented known minor limitation** (below).

**v0.6 (Hardening) is COMPLETE.** v0.6.0 → v0.6.10 done. The skill is autonomous end-to-end: process → validate → auto-heal → finalize, with status/retry/dry-run/repair tooling and an advisory tag linter.

### Known minor limitations (accepted, not blocking)
- **Archive↔chat back-reference**: ~2 residual asymmetric links where an `_archive_*` references a `chat_*` in its body. Cosmetic, non-blocking (REVIEW not FAIL). A clean fix needs a model that distinguishes "consolidation dump body ref" from "semantic link" — deferred indefinitely; not worth a regression.

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
