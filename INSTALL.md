# Installing synthmem

## Requirements

- **Claude Code** installed and working (`claude --version`).
- A directory where your vault will live. This can be:
  - A local folder
  - A folder synced via Dropbox / iCloud / Syncthing
  - A git-tracked folder (recommended — versioned history of your memory)
- **Obsidian** (optional, for graph view and pretty reading).

### Optional acceleration: Python 3.8+

The skill ships with helper scripts in `skill/scripts/` that parse Claude Code session transcripts and update state files atomically. If Python 3.8+ is on your PATH, the skill uses them and runs are noticeably faster and cheaper in tokens.

**Without Python**, the skill falls back to inline AI parsing — it still works, just slower and more token-expensive per run. No action needed; the skill detects what's available at runtime.

Check if you have Python 3:
```bash
python3 --version
```
If it prints `Python 3.8.x` or higher, you're set.

## Steps

### 1. Clone this repo

```bash
git clone <this-repo-url> px-skill-synth
cd px-skill-synth
```

### 2. Configure your local settings

Copy the example config and edit it to point at your vault:

```bash
mkdir -p _local
cp config.example.json _local/config.json
```

`config.example.json` (at the repo root) is the public template — safe to read, no personal data. Your real config lives in `_local/config.json` which is gitignored.

Edit `_local/config.json`:

```json
{
  "vault_path": "/absolute/path/to/your/vault",
  "vault_name": "my-synth-vault",
  "claude_sessions_dir": "~/.claude/projects",
  "default_project_tag": "personal",
  "owner_handle": "your-handle-or-name",
  "timezone": "Etc/UTC"
}
```

`_local/` is gitignored, so this file never leaves your machine.

### 3. Install the skill

Symlink (recommended — updates from `git pull` propagate automatically) or copy:

```bash
# Symlink (preferred)
ln -s "$PWD/skill" ~/.claude/skills/synthmem
ln -s "$PWD/commands/synthmem.md" ~/.claude/commands/synthmem.md

# Or copy
cp -r skill ~/.claude/skills/synthmem
cp commands/synthmem.md ~/.claude/commands/synthmem.md
```

### 4. Initialize your vault

First-time setup creates the scaffolding (`_INDEX.md`, `_RECENT.md`, `_state.json`, README):

```bash
cd /path/to/your/vault
claude
> /synthmem init
```

### 5. Run it

Whenever you're ready to consolidate (typically end of day):

```bash
> /synthmem
```

If you skipped a few days, it will catch up automatically — no flags needed.

## Verifying the install

Right after init, before the first real run, your vault looks like this:

```
my-synth-vault/
├── README.md
├── _INDEX.md
├── _RECENT.md
└── _state.json
```

After the first `/synthmem` run with content, the lazy subdirectories appear:

```
my-synth-vault/
├── README.md
├── _INDEX.md
├── _RECENT.md
├── _state.json
├── nodes/
│   └── node_*.md           (concepts distilled from sessions)
├── entities/
│   └── entity_*.md         (people/tools/projects identified)
├── chats/
│   └── chat_YYYYMMDD_*.md  (one per session)
└── logs/
    └── log_YYYYMMDD.md     (one per run-day)
```

`archives/` appears only after the first compaction (≥ 7-day-old logs/chats exist).

## Troubleshooting

- **`/synthmem` not recognized**: confirm the symlinks resolve (`ls -l ~/.claude/commands/synthmem.md`).
- **Skill can't find sessions**: check `claude_sessions_dir` in `_local/config.json`. On Linux/macOS it is typically `~/.claude/projects/`.
- **Vault not being written**: check `vault_path` is absolute and writable.
- **Permission errors on `.git/`**: synthmem will not touch `.git/`, `.gitignore`, or any file matching gitignore patterns inside the vault. If you see errors, file an issue.
