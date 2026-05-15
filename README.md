# synthmem — Synthetic Memory Skill for Claude Code

A Claude Code skill that turns your Claude conversations into a **persistent, auto-managed, plain-Markdown vault** — a "third brain" you can read with any editor, browse as a graph in Obsidian, and recover from disk if the cloud disappears.

> **Status:** v0.5 (working scaffold, debugging). Designed to be shared. Pull requests welcome.

## Philosophy

Most "memory" skills for AI assistants try to read everything every session, treating the vault as live context. This one is different:

- **The AI feeds the vault; the user (and the AI on demand) reads from it.** Not every session triggers a write. You decide when to consolidate (typically once a day) by running `/synthmem`.
- **The vault outlives the tool.** Plain `.md` files, hybrid layout (semantic core at root, transient files in lazy subdirs), YAML frontmatter, wikilinks. No proprietary format. No images, no binaries, no embedded media — only references to them. If Claude Code disappears tomorrow, your vault still works in Obsidian, VS Code, `grep`, or any text editor.
- **The AI is the curator, not the gatekeeper.** It organizes, links, tags, compacts. You read.
- **Privacy first.** The skill ships with zero personal data. Everything user-specific lives in `_local/` (gitignored) and is referenced via placeholders.

## What it does

When you run `/synthmem`:

1. **Detects** the last time it ran. On the very first run, asks once: only today, full history, or a custom window.
2. **Reads** every Claude Code session between then and now.
3. **Dispatches multiple sub-agents** to extract concepts, entities, decisions, and code patterns from those sessions.
4. **Writes** them into a hybrid-Markdown vault — `node_*` and `entity_*` at the root; `chat_*` in `chats/`; `log_*` in `logs/`. Each file uses a 5-tag frontmatter (3 domain + 1 content-type + 1 project).
5. **Links** related concepts bidirectionally with `[[wikilinks]]` (basenames, portable across subdirs).
6. **Compacts** old daily logs and chats into `archives/_archive_*.md` — **without deleting** anything.
7. **Updates** the index so you (and future Claude sessions) can find what's there.
8. **Resilient**: progress is checkpointed day-by-day in `_state.json`. If the run is interrupted, the next invocation picks up where it left off.

Subdirectories (`chats/`, `logs/`, `archives/`) are created **lazily** — only when there is real content to put inside.

You can leave it running overnight. After the first-run prompt, it does not ask questions; it just works.

## What it is not

- **Not a real-time memory.** It does not hook every session.
- **Not a chatbot wrapper.** No proprietary indexing, no embeddings, no vector DB.
- **Not destructive.** Nothing is ever deleted; old material is archived with provenance.
- **Not a cloud service.** Your vault lives wherever you put it (local folder, Dropbox-synced folder, git repo — your call).

## Install

See [INSTALL.md](INSTALL.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Why "synthmem"?

Short for *synthetic memory*. The vault is not "the AI's brain" — it's an externalized, file-based supplement to your own memory, *synthesized* automatically from your work with the AI.

The concept of a "third brain" (after biological + curated digital like Obsidian) inspired the design, but the name stays technical on purpose.

## License

AGPL-3.0-or-later — see [LICENSE](LICENSE).

## Acknowledgments

The hybrid-directory + frontmatter + wikilinks design draws on long-standing PKM patterns (Zettelkasten, Obsidian conventions) and on public proofs-of-concept circulating in the AI community in 2025–2026. This implementation diverges by being **user-triggered** rather than session-hooked, and by treating the vault as **archival** rather than live context.
