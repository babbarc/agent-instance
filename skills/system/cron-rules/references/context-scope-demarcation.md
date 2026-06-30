# Context Scope Demarcation — WhatsApp Delta Implementation

Concrete implementation of the "Context vs Actionable Data" pattern from the
cron-rules SKILL.md, based on the heartbeat-watchdog cron session (2026-06-15).

## Problem

`whatsapp_delta.py` injects `CONTEXT_DEPTH=7` pre-window messages per 1:1
conversation (for LLM thread understanding). These are printed sequentially
before in-window messages with no demarcation. The heartbeat prompt (v38)
has no rule telling the LLM to ignore them — so old context messages get
triaged, routed, and reported alongside actual new messages.

## Fix — whatsapp_delta.py

Replace the unconditional context+window dump (lines 685-690) with conditional
markers:

```python
ctx = list(context_buf.get(jid, []))
if ctx:
    print("[context]")
    for msg in ctx:
        print(msg)
    print("[window]")
for msg in window_msgs[jid]:
    print(msg)
```

**Why square brackets:** Conversation headers use `--- Alice ---` format.
`--- CONTEXT ---` would visually collide. `[context]` / `[window]` are
structurally distinct from the header format.

**Why conditional:** If a conversation has no pre-window context, all messages
are in-window and nothing can be misreported — no markers needed.

## Fix — Prompt Rule

Add after the Empty State Guard in the cron prompt:

```
**Reporting Scope:** Only triage, route, report, and enrich contacts based on
items within the current heartbeat window.

- **WhatsApp:** A conversation may have a `[context]` / `[window]` block pair.
  Messages between `[context]` and `[window]` are pre-window thread context
  only — do NOT triage, route, report, or enrich from them. Messages after
  `[window]`, or all messages if no `[context]` block appears, are in-window
  and fully actionable.
- **Email / Calendar:** All items are within the time window.
```

## Edge Cases

- **No context for a conversation:** No markers emitted. All messages actionable.
  The LLM receives a clean block with no `[context]` or `[window]` — prompt
  rule says "all messages if no [context] block appears = actionable."
- **Group chats:** Context is never loaded for groups (line 657: `if "@g.us"
  not in jid`). No markers emitted, all group messages actionable.
- **Multiple conversations:** Each conversation gets independent markers.
  One conversation may have `[context]`/`[window]` while another has none.
- **Empty conversation (no window messages):** Both context_buf and window_msgs
  are empty for that JID — it was never added to `active_jids`, so no output
  at all.
