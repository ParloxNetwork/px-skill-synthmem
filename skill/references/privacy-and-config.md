# Privacy and configuration

The skill is designed to be **shared publicly** (open source on GitHub). The vault is the user's **private** intellectual content. These two facts shape every privacy decision below.

## Golden rule

> The public skill repo must never contain a path, name, email, project, or any other personal identifier of any specific user.

If you (the AI) are about to write a personal value into a file that lives inside `skill/` or `commands/` or the repo root, **stop**. That value belongs in `_local/config.json`.

## Where personal data lives

| Where | What | Committed to public repo? |
|---|---|---|
| `_local/config.json` | The user's vault path, owner handle, timezone, project tag, agent toggles. | ❌ No — `_local/` is in `.gitignore`. |
| `_local/taxonomy.overrides.md` | The user's pinned tag vocabulary. | ❌ No. |
| `_local/notes.md` | The user's scratch notes about how they personally use the skill. | ❌ No. |
| The vault itself | All content extracted from sessions. | The user decides. The skill never assumes. |
| `skill/**/*` and `commands/synthmem.md` | Skill logic, templates, references. | ✅ Yes — and must contain zero personal data. |

## Reading config at runtime

On every invocation, resolve config from `_local/config.json`. If it is missing:

1. **Tell the user explicitly** that the file is missing.
2. Point them at the public template (`config.example.json` at the skill repo root) and `INSTALL.md`.
3. Do not invent defaults for `vault_path` or `claude_sessions_dir` — abort instead. Inventing a default risks writing the vault somewhere unexpected.

If config is present but a field is missing, use the documented default (see `config.example.json` at the repo root as the source of truth for defaults).

## Placeholders used inside the skill

When the skill needs to reference a configurable value in its own prose, use these placeholders. Resolve them at runtime; never hardcode.

| Placeholder | Resolves to |
|---|---|
| `${VAULT_PATH}` | `config.vault_path` — absolute path to the vault root. |
| `${VAULT_NAME}` | `config.vault_name` — the user's chosen name for their vault. |
| `${CLAUDE_PROJECTS_DIR}` | `config.claude_sessions_dir` — typically `~/.claude/projects`. |
| `${OWNER_HANDLE}` | `config.owner_handle` — used in commit messages, vault README, etc. |
| `${TIMEZONE}` | `config.timezone` — IANA timezone (e.g., `Europe/Berlin`, `America/New_York`). |
| `${PROJECT_TAG}` | `config.default_project_tag` — fallback when a session has no clearer context. |

## What never leaves the user's machine

- The contents of their vault (unless they push their private vault repo themselves).
- The contents of `_local/`.
- Session transcripts.
- Anything inferred from sessions (concepts, entities, decisions).

The skill itself does **no network I/O**. Everything is local file operations.

## Logging hygiene

If the skill prints status to stdout or writes a log to `log_*.md`:

- ✅ Print **counts and slugs**: "Created 3 new nodes: `node_foo`, `node_bar`, `node_baz`."
- ❌ Do not print full file paths, absolute or otherwise. The user knows their vault location.
- ❌ Do not echo session contents verbatim.
- ❌ Do not include `owner_handle` in any file inside `skill/` — it is fine inside the vault (the vault is the user's own).

## Generic skill content

When writing any file inside `skill/` or `commands/`, use generic examples:

- ✅ "a sermon outline on the doctrine of justification"
- ✅ "a code pattern for Claude Code skill structure"
- ❌ "Jane's sermon at FirstChurch on 2026-05-13" (specific name, place, date)
- ❌ "/home/some-user/vault" (specific user path)

Anything specific belongs in a comment in `_local/` or in the vault itself.

## Vault privacy mode

The user's vault may itself be public or private. The skill does **not** decide. The skill simply respects whatever `.gitignore` exists inside the vault and never overrides it.

If the user wants to mark certain content as private-within-the-vault, they can:

1. Add a `private:` field to frontmatter (any truthy value).
2. The indexer (in v0.6+) will optionally exclude `private: true` files from `_INDEX.md` summaries.

For v0.5, this is a documented convention — not yet enforced.

## What the skill commits to git

The skill never runs `git` commands against the vault on its own. Versioning the vault is the user's responsibility. If they want auto-commit, they can wire it up themselves (a `post-run` shell hook is on the v0.3 roadmap).

The skill **may** read `.git/` to detect that the vault is a git repo (purely informational, for the run report). It never **writes** to `.git/`, `.gitignore`, or `.gitattributes`. See `vault-structure.md` for the full off-limits list.

## When in doubt

Stop and ask the user. Privacy violations cannot be undone after a public push.
