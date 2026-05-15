# Multi-agent orchestration

Synthmem runs as a pipeline of specialized sub-agents. Each does one thing well; the orchestrator (you, the main skill invocation) coordinates them.

## Why multi-agent

A single long-running Claude session would carry the entire vault, all session transcripts, and all reasoning in one context. That's expensive, slow, and fragile. Splitting the work:

- Each sub-agent has a tight, focused prompt.
- Failures are isolated (a broken distiller doesn't corrupt the indexer's work).
- The main session orchestrates and reports — it doesn't need to hold every transcript in its context.

## The pipeline

```
                      ┌─────────────┐
   _state.json   ───→ │  orchestrator  ──→ end-of-run report
   _local/config      │   (this skill)  │
                      └────┬────────┘
                             │
                ┌───────────┼───────────┐
                ▼            ▼            ▼
          ┌─────────┐  ┌─────────┐  ┌─────────┐
          │harvester│→ │distiller│→ │ linker  │ → ┌─────────┐
          └─────────┘  └─────────┘  └─────────┘    │ indexer │
                                                    └─────────┘
```

## Sub-agent specs

### 1. `harvester`

**Job:** Read raw Claude Code session files in the date range and produce `chat_*.md` references (one per session).

**Inputs (passed in prompt):**
- Date range (`from`, `to`)
- `claude_sessions_dir` (from config)
- Vault path

**Outputs:**
- One `chats/chat_YYYYMMDD_<short-id>.md` per session (creates `chats/` lazily on first write), with:
  - Frontmatter (type: chat, tags including session topic guesses, content-type: `summary`)
  - A ~5–15 line distilled summary of what the session was about
  - Pointers to the raw `.jsonl` file (path only, not embedded)
  - Lists of candidate concepts and entities for the distiller to pick up
- A handoff JSON listing the `chat_*` files it produced + concept/entity candidates

**Must not:** create `node_*` or `entity_*` files (that's the distiller's job).

### Handling long sessions (chunking rule)

A single Claude Code session can have hundreds of turns. Loading all of them into a distiller's context at once is wasteful and may overflow the budget.

**Rule**: if a session has more than **100 turns**, the distiller MUST process it in chunks of 50 turns:

1. Read turns 1–50 → produce intermediate summary `chunk_1`.
2. Read turns 51–100 → produce `chunk_2`, given `chunk_1` as context.
3. Continue until all turns are covered.
4. Synthesize the final `chat_*.md` from the chunk summaries.

This responsibility lives **inside the distiller sub-agent**, not the orchestrator. The chunking is invisible from outside — the distiller still produces exactly one `chat_*.md` per session.

For sessions ≤ 100 turns, the distiller processes them in one pass.

### 2. `distiller`

**Job:** Take the candidate list from the harvester and produce/update `node_*.md` and `entity_*.md` files.

**Inputs:**
- The harvester's handoff JSON
- Vault path (for checking what already exists)
- Tag taxonomy reference

**Outputs:**
- New `node_*.md` files for concepts not yet in the vault
- **Append blocks** to existing `node_*.md` files when the concept already exists (do not overwrite — append a dated section)
- Same for `entity_*.md`
- A handoff JSON listing files created and files updated, with the wikilinks each contains

**Must not:**
- Overwrite existing `node_*` or `entity_*` files entirely. Append, or refactor only if explicitly justified in the handoff JSON.
- Duplicate concepts under near-identical slugs (`node_justification` vs `node_justification-doctrine`). Search the vault first; reuse the existing slug.

### Distiller quality bar — strict promotion criteria (v0.6.1)

A common failure mode in v0.6.0 was over-fragmentation: a single session produced 30+ `node_*` files for concepts that were one-shot mentions or implementation details. To prevent this, **a concept is promoted to a standalone `node_*.md` only if at least one of these holds**:

1. **Recurrence**: the concept appears in **≥ 2 distinct sessions** (cross-references in `sources:` of an existing node, or two different chat transcripts in this run).
2. **Substantive content**: the distilled material is **≥ 200 words** when written out — concrete enough to be a knowledge atom, not a passing reference.
3. **Explicit user marking**: the user said "save this" / "remember this" / "note that" in the session.

If none holds, the concept becomes either:
- A bullet under "Concepts touched" in the relevant `chat_*.md` (default), **or**
- An `## Update YYYY-MM-DD` section appended to an existing related `node_*.md` (preferred when there is a clear parent concept).

### Conservative merging — only when truly the same concept

Before creating `node_<slug>`, the distiller checks for an existing node that is **the same concept**, not merely one that shares a leading word. Merge **only** if **both** hold:

1. **Slug containment**: one slug is a strict prefix of the other (`node_justification` vs `node_justification-doctrine`) OR the titles are near-identical (case/stopword-insensitive).
2. **Content overlap**: the two cover the same core idea, not two different aspects of a shared umbrella.

Do **NOT** merge solely because slugs share a leading token. These are distinct concepts and must stay separate:
- `node_claude-code-memory` vs `node_claude-code-greeting` — different topics; keep both.
- `node_sermon-skill-flow` vs `node_sermon-spa-modes` — different aspects; keep both.

When two nodes are related but distinct, **do not merge — link them** (add each to the other's `linked_nodes`; the linker enforces this).

When uncertain, **keep separate and link**. A wrong merge destroys information and is hard to undo; an extra link is cheap and reversible.

The same rule applies to `entity_*` files.

### Why this matters

Without the quality bar, a single active day floods the vault with low-signal nodes. After 30 days you have hundreds of files most of which are one-line concepts. The vault becomes harder to navigate than the chat transcripts themselves — defeating the point.

### 3. `linker`

**Job:** Build the knowledge graph. This is the linker's core value — without it the vault is a pile of disconnected notes, not a "third brain". The linker has **two phases**; phase 2 is the one that was missing in v0.6.1 and matters most.

**Inputs:**
- The distiller's handoff JSON
- Vault path (full read access to `nodes/`, `entities/`, `chats/`)

#### Phase 1 — provenance bidirectionality (chat ↔ node/entity)

- For each file touched this run, parse its `sources:` and `linked_nodes:`.
- For every `[[target]]`, open the target and ensure the reverse reference exists.
- This is necessary but **not sufficient**. A vault where nodes only connect through chat hubs has a star topology, not a knowledge graph.

#### Phase 2 — semantic node↔node linking (REQUIRED, was missing)

For every `node_*` / `entity_*` written or touched this run, establish links to other **nodes/entities** (not just chats):

1. **Explicit mention**: if node A's body names a concept that has its own `node_B` (slug, title, or a declared synonym appears in A's prose), add `[[node_B]]` to A's `linked_nodes` and `[[node_A]]` to B's. Bidirectional, always.
2. **Shared-domain affinity**: if two nodes share **≥ 2 of their 3 domain tags** AND their content is topically related (not just coincidentally co-tagged), link them.
3. **Parent/child**: if one node is a specialization of another (e.g., `node_compaction-policy` ⊂ `node_vault-hybrid-layout`), link both ways.

**Bounds (avoid the hairball):**
- Max **7** `linked_nodes` per file. If more candidates exist, keep the strongest (explicit mention > parent/child > shared-domain).
- Never link a node to itself.
- Shared-domain affinity alone, with no content relation, is **not** enough — require a real conceptual relationship. Tag co-occurrence is a hint, not a link.

**Acceptance check before finishing:** if more than ~30% of nodes touched this run still have `linked_nodes: []`, the linker has under-performed — re-scan those isolated nodes for phase-2 candidates before handing off. An isolated node is a linker failure, not a normal outcome.

#### Broken / dangling wikilinks

- A `[[target]]` with no matching file is **left as-is** (unresolved). It is a deliberate anchor: Obsidian shows it as "create new", and a future run that creates the target auto-resolves it (basenames match).
- Do **not** create `status: draft` stub files for dangling links — that clutters the vault with empties.
- **Exception**: if the same dangling target is referenced by **≥ 3 distinct files**, that is a strong signal the concept matters → create one real `status: draft` node with a `TODO: define` and link it. Report it.
- Report the count of unresolved links in the handoff (informational, not an error).

**Outputs:**
- Updated files (`linked_nodes` and `last_updated` only; never rewrites body content).
- A handoff JSON: phase-1 backlinks added, phase-2 semantic links added, dangling-link count, any draft stubs created (with the ≥3 reason).

### 4. `indexer`

**Job:** Update `_INDEX.md`, `_RECENT.md`, `_state.json`, run compaction.

**Inputs:**
- All previous handoffs
- Vault path
- Compaction policy reference

**Outputs:**
- `_INDEX.md` regenerated from a scan of all `node_*` and `entity_*` frontmatter.
- `_RECENT.md` updated with the last 14 days of activity (older entries dropped from this file but never from the vault).
- `_state.json` `last_run` bumped to "now".
- Compaction performed per `compaction-policy.md`.
- A final summary appended to today's `logs/log_YYYYMMDD.md` (creates `logs/` lazily on first write).
- `_state.json` updated **after each day completes**, not only at the very end — see `catch-up-logic.md` for the resilience model.

### 4b. Validation gate (always, not optional)

After the indexer finishes and before the run is finalized, run the deterministic validator **scope-aware** — pass the list of files this run wrote/touched (collected from the harvester/distiller/linker/indexer handoffs):

```bash
python3 ${SKILL_DIR}/scripts/validate_vault.py \
  --vault ${VAULT_PATH} \
  --changed "logs/log_20260515.md,nodes/node_x.md,chats/chat_..._....md,..."
```

(If Python is unavailable, perform the equivalent checks inline — see `validate_vault.py`'s docstring.)

- Parse the JSON `summary`. Append it to today's `logs/log_YYYYMMDD.md`.

**Auto-heal loop (v0.6.6 — the gate now self-heals, it doesn't just accuse):**

1. If validation is clean (PASS, no fixable issues) → skip straight to finalize. Zero extra cost on healthy vaults.
2. If validation reports **any deterministically-fixable issue** (tag distinctness, slug≠filename-tail, asymmetric wikilinks, archive content-type, markdown `<…>`), legacy *or* in-scope:
   - Run `python3 ${SKILL_DIR}/scripts/repair_vault.py --vault ${VAULT_PATH} --project ${PROJECT_TAG}`.
   - **Re-run** the validator (same `--changed` scope).
   - Log what repair fixed, split: **legacy** (note count, expected) vs **in-scope** (the distiller/linker produced fixable output → log `⚠ distiller-smell: investigate`; keeps the dev-observability signal even though the user's vault silently healed).
3. After re-validation:
   - **Zero errors** → finalize normally.
   - **Residual in-scope errors repair could not fix** → `last_run_status: "partial"`, list them, surface to user.
   - **Only non-auto-fixable `flagged` items** (e.g. genuine duplicate-domain-tags needing a semantic re-tag) → **finalize anyway**. These never block (blocking = stuck overnight state = anti-autonomy). They go to the log's `## Para revisar (opcional)` section and one concrete line in the final user summary.

`/synthmem repair` standalone still exists for manual/debug use, but the autonomous pipeline no longer requires the user to invoke it.

Why scope still matters: in-scope vs legacy is now used for the **observability split** (is the distiller producing fixable junk?), not for blocking. Repair handles both; the gate's job shrinks to "finalize, or surface the genuinely-human-only items."

This replaces ad-hoc LLM "sanity checking" with a deterministic, reproducible gate — the same reason the other scripts exist (v0.6.0 principle: mechanical work is scripted, not eyeballed).

### 5. `reviewer` (optional, off by default)

The validator (4b) covers the mechanical checks. The optional `reviewer` adds **semantic** review the validator can't do: is a node actually substantive, are tags *accurate* (not just well-formed), did the distiller miss an obvious concept. Flags only — never auto-corrects. Enable via `_local/config.json` → `agents.reviewer: true`.

## Dispatch

When the work is non-trivial (> 1 day of sessions, or > 5 sessions in any day), dispatch sub-agents using the `Agent` tool. For trivial runs (first-time init, single short session), do the work inline.

Each sub-agent's prompt should include:
- A clear scope statement ("you are the X; do only X")
- The handoff inputs (passed as literal text or file paths)
- Pointers to the relevant reference files in this skill
- A schema for the handoff output JSON

Sub-agents must **not** call the main `/synthmem` recursively.

## Dry-run behavior

When the run is `--dry-run`, the pipeline still executes but in plan-only mode:

- **harvester**: runs normally — it is already read-only (parses JSONL, writes nothing to the vault). Produces the same handoff.
- **distiller**: runs a **planning pass**. It decides, per concept: create vs update vs merge, the target slug, the 5 tags, the candidate wikilinks. It does **not** generate full bodies and does **not** write files. Its handoff lists intended actions only.
- **linker**: computes the edges it *would* add (count + sample) from the distiller's plan. Writes nothing.
- **indexer**: does **not** regenerate `_INDEX.md`/`_RECENT.md`, does **not** call `update_state.py`, does **not** compact. It computes what it *would* archive and folds the whole plan into the single chat-only report (see SKILL.md `--dry-run`).
- **validation gate**: runs `validate_vault.py` against the *current* (unchanged) vault to give a baseline, and predicts the post-run verdict from the plan. No state change.

The orchestrator is responsible for enforcing the "write nothing" guardrail even if a sub-agent misbehaves: in dry-run, reject any handoff that claims to have written a file.

## Failure modes

If a sub-agent fails:
- The orchestrator keeps whatever the previous agents produced (no rollback).
- Today's log records the failure in `WARNINGS`.
- The user can rerun `/synthmem` and the catch-up logic will reprocess what was missed.

Never leave the vault in an inconsistent state: if you cannot complete the run, at minimum ensure `_state.json.last_run` is **not** updated (so the next run reprocesses the same range).
