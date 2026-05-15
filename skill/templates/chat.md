---
id: YYYYMMDD-HHMMSS-xxx
type: chat
title: "<one-line session summary>"
slug: YYYYMMDD-<short-id>
session_id: <session-uuid>
started_at: YYYY-MM-DDTHH:MM:SS-HH:MM
ended_at: YYYY-MM-DDTHH:MM:SS-HH:MM
turn_count: 0
working_directory: "<redacted-unless-opted-in>"
tags:
  - <specific-domain-1>
  - <specific-domain-2>
  - <specific-domain-3>
  - summary
  - <project-tag>
status: active
linked_nodes:
  - "[[node_concept-from-session]]"
sources:
  - external: "session-jsonl:<filename>"
created: YYYY-MM-DDTHH:MM:SS-HH:MM
last_updated: YYYY-MM-DDTHH:MM:SS-HH:MM
---

# <one-line session summary>

> **Session date**: YYYY-MM-DD
> **Duration**: ~N minutes
> **Tool**: Claude Code (`<model-id>`)

## What the session was about

<3–8 sentence distillation. What did the user ask? What did they decide? What did they learn? Optimized so that a future Claude session can grok this without re-reading the raw `.jsonl`.>

## Concepts touched

- [[node_x]] — how it came up
- [[node_y]] — how it came up

## Entities mentioned

- [[entity_z]]

## Decisions made

- **Decision**: <what>. **Reasoning**: <why>. **Status**: <enacted | pending | reverted later>.

## Outcomes

- <Code shipped, document written, problem solved, blocker hit. Be concrete.>

## Open threads

- <What's still pending after this session?>

## Notable turns

<Optional. Quote 1–3 specific user/assistant exchanges that were pivotal. Use blockquotes. Do not quote the full session.>

> **User**: ...
>
> **Assistant**: ...

## Raw transcript

Located at: `<session-jsonl path or "see session_id">` — not embedded here.

## User notes

<Reserved for the user. The AI never writes below this heading.>
