# Session source — Claude Code transcripts

How and where Claude Code stores conversation history, and how the harvester reads it.

## Storage location

Claude Code persists session transcripts as JSONL files under `~/.claude/projects/`. The exact path is configurable via `_local/config.json` (`claude_sessions_dir`); default is `~/.claude/projects/`.

Layout:

```
~/.claude/projects/
├── -home-user-repo-foo/                # encoded path of the project's cwd
│   ├── <session-uuid-1>.jsonl
│   ├── <session-uuid-2>.jsonl
│   └── ...
├── -home-user-repo-bar/
│   └── <session-uuid>.jsonl
└── ...
```

The directory name is the project's working directory with `/` replaced by `-` (a Claude Code convention). Each `.jsonl` file is one Claude Code session.

## Decoding the directory name

To recover the working directory from a directory name:

1. Take the name.
2. If it starts with `-`, the leading `-` represents the root `/`.
3. Replace remaining `-` with `/`.

Example: `-home-user-pxdev-foo` → `/home/user/pxdev/foo`.

(In rare cases, an actual hyphen in the path can be ambiguous; the synthmem harvester treats the encoded name as opaque and uses the JSONL contents for ground truth where needed.)

## JSONL format

Each line is one event. The events that matter for synthmem:

| `type` | Meaning | Key fields |
|---|---|---|
| `summary` | Session-level metadata (often the first line) | `summary`, `leafUuid` |
| `user` | User message | `message.content`, `timestamp`, `cwd` |
| `assistant` | Assistant response | `message.content`, `timestamp`, `model` |
| `tool_use` / `tool_result` | Tool invocations and results | various |
| `system` | System reminders, hooks | `content`, `subtype` |

Other event types may exist; the harvester ignores types it doesn't recognize.

## Time range filtering

Each event has a `timestamp` in ISO 8601. The harvester filters by:

```
timestamp >= from && timestamp <= to
```

A session is considered "in range" if **any** event falls in the range. The harvester includes the whole session even if only a few events match — context is needed to distill.

## Working-directory filtering (optional)

By default, the harvester processes sessions from **every** project directory. The user can scope a run with:

```
/synthmem --cwd /absolute/path/to/project
```

…to limit to one project's sessions. (v0.2.)

## Reading strategy

For each session in range:

1. Read the JSONL file line by line (do not load all events into memory if the file is huge — stream).
2. Group events into turns (a turn = one user message + the assistant's response + any tool use in between).
3. Pass to the distiller as a structured object:

```json
{
  "session_id": "01HXY-...",
  "started_at": "2026-05-14T08:12:00-05:00",
  "ended_at": "2026-05-14T09:34:00-05:00",
  "cwd": "/absolute/path/to/project",
  "summary_hint": "<the `summary` event's content, if any>",
  "turn_count": 47,
  "turns": [ ... ]
}
```

The distiller does the actual content extraction; the harvester just structures.

## Privacy considerations

Session transcripts contain *everything* the user typed and Claude said. This includes:

- File paths, including personal paths
- Code snippets that may contain secrets
- Personal names, emails, conversation topics

The harvester must:

1. **Pass content through to the distiller without writing it to disk anywhere in the skill repo.** The skill repo is public; raw session text never goes there.
2. **The distiller's output (chat / node / entity files) may quote session content**, but only into the vault, which is the user's private space.
3. **Working directory paths** in `chat_*.md` frontmatter: write them only if the user opted in (`config.json` → `record_cwd_in_chats: true`, default `false`). Otherwise replace with `<redacted>`.

## Reliability

JSONL files are append-only during a live session. Reading them while Claude Code is running is safe (line-based; partial last line is ignored). Stale or corrupted files: skip with a warning rather than fail the whole run.

## Future: non-Claude sources

When v0.3 adds Codex / Gemini adapters, this file will gain a section per source. The harvester contract stays the same — emit structured turn-lists. The source-specific parsing details live in adapter docs.
